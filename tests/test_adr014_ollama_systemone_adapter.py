"""The `ollama_systemone` adapter: typed questions, probabilities back, and the models a run brings. See ADR 014 §2.

The server these tests run against keeps real residency, as the `lmstudio` tests' server does: a call
puts the model on it, a keep-alive of zero takes it off, and the listing reports what it holds. The
release rules are then measured by asking the server what is still loaded. The refusals it scripts are
the bodies a real Ollama server returned in session `2026-10-28-implementation-1`.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import MappingProxyType

import pytest

import workflow_engine.codecs.base_codecs  # noqa: F401 - registers the codecs the declarations resolve
from workflow_engine.actions.action_llm import LlmAction
from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.models.state import StateModel, StateReadOnlyView
from workflow_engine.providers.base_provider import (
    FinalizeReason,
    ProviderCall,
    ProviderErrorClass,
    ProviderSettings,
)
from workflow_engine.providers.provider_seat import finalize_providers, install_provider_settings
from workflow_engine_providers.ollama_systemone import (
    ADAPTER_NAME,
    OllamaResidencyError,
    OllamaSystemOneProvider,
    reset_residency,
)

MODEL = "a-decision-model:small"
FOREIGN_MODEL = "a-chat-model:3b"

NOUL = {"type": "noul", "instructions": "Is 12345 a trip identifier this message asks to book money against?"}
CHOICE = {"type": "choice", "instructions": "What does it ask?", "criteria": {"pay": "to pay", "cancel": "to cancel"}}
SCORE = {"type": "score", "instructions": "How urgent?", "criteria": ["low", "mid", "high"]}

OVERFLOW_REFUSAL = (
    "the prompt is longer than the context length currently available to the model; shorten the prompt, "
    "adjust the context length in settings, or use a model with a longer context length"
)
NOT_A_DECISION_MODEL = 'model "a-chat-model:3b" is not a llama.cpp decision model'


def answer_of(question: dict[str, object]) -> dict[str, object]:
    """What the server answers for one question type, in the shape the API reference states."""
    if question["type"] == "noul":
        return {"type": "noul", "noul": 0.9163}
    if question["type"] == "choice":
        return {"type": "choice", "choice": "pay", "probabilities": {"pay": 0.99, "cancel": 0.01}, "confidence": 0.98}
    return {
        "type": "score",
        "score": 1.15,
        "legend": {"0": "low", "1": "mid", "2": "high"},
        "probabilities": {"0": 0.15, "1": 0.55, "2": 0.30},
        "confidence": 0.32,
    }


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def _respond(self, status: int, payload: object) -> None:
        encoded = (payload if isinstance(payload, str) else json.dumps(payload)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        self.server.requests.append(("GET", self.path, {}, dict(self.headers)))
        if self.path == "/api/ps" and self.server.fail_listing is None:
            self._respond(200, {"models": [{"name": name, "model": name} for name in sorted(self.server.loaded)]})
        elif self.path == "/api/ps":
            self._respond(self.server.fail_listing, {"error": "scripted refusal"})
        else:
            self._respond(404, {"error": "no such path"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        self.server.requests.append(("POST", self.path, body, dict(self.headers)))
        if self.path == "/v1/systemone":
            self._systemone(body)
        elif self.path == "/api/generate":
            self._generate(body)
        else:
            self._respond(404, {"error": "no such path"})

    def _systemone(self, body: dict[str, object]) -> None:
        if self.server.delay:
            time.sleep(self.server.delay)
        if self.server.refusal is not None:
            self._respond(*self.server.refusal)
            return
        model = str(body["model"])
        if body.get("keep_alive") != 0:
            self.server.loaded.add(model)
        questions = body["questions"]
        self._respond(
            200,
            {
                "model": model,
                "answers": {name: answer_of(question) for name, question in questions.items()},
                "usage": {"input_tokens": 174, "output_tokens": 1},
            },
        )

    def _generate(self, body: dict[str, object]) -> None:
        if self.server.fail_unload is not None:
            self._respond(self.server.fail_unload, {"error": "scripted refusal"})
            return
        if body.get("keep_alive") == 0 and not body.get("prompt"):
            self.server.loaded.discard(str(body["model"]))
        self._respond(200, {"model": body["model"], "response": "", "done": True, "done_reason": "unload"})

    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output free of the server's access log."""
        return


class FakeOllama(ThreadingHTTPServer):
    """A loopback Ollama that answers System One calls and keeps what it has loaded."""

    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.requests: list[tuple[str, str, dict[str, object], dict[str, str]]] = []
        self.loaded: set[str] = set()
        self.refusal: tuple[int, object] | None = None
        self.fail_listing: int | None = None
        self.fail_unload: int | None = None
        self.delay = 0.0

    @property
    def base_url(self) -> str:
        host, port = self.server_address[0], self.server_address[1]
        return f"http://{host}:{port}/v1"

    def calls(self) -> list[dict[str, object]]:
        return [body for method, path, body, _ in self.requests if path == "/v1/systemone"]

    def unloads(self) -> list[str]:
        return [str(body["model"]) for method, path, body, _ in self.requests if path == "/api/generate"]


@pytest.fixture(autouse=True)
def residency_guard() -> Iterator[None]:
    """The residency registry is module state; no test may leave what it brought to the next."""
    reset_residency()
    yield
    reset_residency()


@pytest.fixture
def ollama() -> Iterator[FakeOllama]:
    server = FakeOllama()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def settings_for(base_url: str | None, name: str = "decide", **options: object) -> ProviderSettings:
    return ProviderSettings(
        name=name, adapter=ADAPTER_NAME, base_url=base_url, model=MODEL, options=MappingProxyType(dict(options))
    )


def a_call(model: str = MODEL, prompt: str = "Please pay trip 12345.", **options: object) -> ProviderCall:
    options.setdefault("questions", {"is_trip": NOUL})
    return ProviderCall(prompt=prompt, model=model, options=MappingProxyType(dict(options)))


def closed_port_url() -> str:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}/v1"


class TestTheRequestItSends:
    def test_the_prompt_is_the_state_and_the_questions_travel_as_given(self, ollama: FakeOllama) -> None:
        OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(a_call(prompt="Pay trip 12345."))

        assert ollama.calls() == [{"model": MODEL, "state": "Pay trip 12345.", "questions": {"is_trip": NOUL}}]

    def test_an_option_the_adapter_does_not_own_is_sent_unread_and_the_timeout_is_not(self, ollama: FakeOllama) -> None:
        OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(a_call(timeout=30, a_server_field={"x": 1}))

        sent = ollama.calls()[-1]
        assert sent["a_server_field"] == {"x": 1}
        assert "timeout" not in sent

    def test_the_keep_alive_comes_from_the_node_before_the_provider_block(self, ollama: FakeOllama) -> None:
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url, keep_alive="10m"))

        provider.complete(a_call())
        provider.complete(a_call(keep_alive=0))

        assert [call["keep_alive"] for call in ollama.calls()] == ["10m", 0]

    def test_no_keep_alive_is_sent_where_none_is_declared(self, ollama: FakeOllama) -> None:
        OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(a_call())

        assert "keep_alive" not in ollama.calls()[-1]

    def test_a_declared_credential_is_sent_as_a_bearer_token(
        self, ollama: FakeOllama, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("A_TEST_OLLAMA_KEY", "secret")
        settings = ProviderSettings(
            name="decide", adapter=ADAPTER_NAME, base_url=ollama.base_url, api_key_env="A_TEST_OLLAMA_KEY"
        )

        OllamaSystemOneProvider(settings).complete(a_call())

        headers = [headers for _, path, _, headers in ollama.requests if path == "/v1/systemone"][-1]
        assert headers["Authorization"] == "Bearer secret"


class TestTheReplyItReturns:
    def test_a_noul_answer_is_the_probability_of_yes(self, ollama: FakeOllama) -> None:
        reply = OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(a_call())

        assert not reply.failed
        assert json.loads(reply.text) == {"is_trip": 0.9163}

    def test_several_questions_are_answered_in_one_call_and_the_others_keep_what_the_server_said(
        self, ollama: FakeOllama
    ) -> None:
        reply = OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(
            a_call(questions={"is_trip": NOUL, "kind": CHOICE, "urgency": SCORE})
        )

        answers = json.loads(reply.text)
        assert len(ollama.calls()) == 1
        assert answers["is_trip"] == 0.9163
        assert answers["kind"] == {k: v for k, v in answer_of(CHOICE).items() if k != "type"}
        assert answers["urgency"] == {k: v for k, v in answer_of(SCORE).items() if k != "type"}

    def test_the_model_and_the_token_counts_are_those_the_server_reports(self, ollama: FakeOllama) -> None:
        reply = OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(a_call())

        assert reply.model == MODEL
        assert reply.usage is not None
        assert (reply.usage.prompt_tokens, reply.usage.completion_tokens) == (174, 1)


class TestTheFailuresItClassifies:
    def test_a_call_without_questions_fails_before_reaching_the_server(self, ollama: FakeOllama) -> None:
        reply = OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(a_call(questions={}))

        assert reply.error_class is ProviderErrorClass.INVALID_REQUEST
        assert ollama.calls() == []

    @pytest.mark.parametrize(
        ("status", "body", "expected"),
        [
            (400, {"error": OVERFLOW_REFUSAL}, ProviderErrorClass.CONTEXT_OVERFLOW),
            (413, {"error": "text and schema must not exceed 64 KiB"}, ProviderErrorClass.CONTEXT_OVERFLOW),
            (400, {"error": NOT_A_DECISION_MODEL}, ProviderErrorClass.INVALID_REQUEST),
            (
                400,
                {"error": 'questions.q: "type" must be one of: choice, score, noul'},
                ProviderErrorClass.INVALID_REQUEST,
            ),
            (404, {"error": "model 'nope:1b' not found"}, ProviderErrorClass.INVALID_REQUEST),
            (429, {"error": "too many requests"}, ProviderErrorClass.RATE_LIMITED),
            (500, {"error": "the model failed"}, ProviderErrorClass.TRANSIENT),
            (500, {"error": "Context size has been exceeded."}, ProviderErrorClass.CONTEXT_OVERFLOW),
            (200, "not json at all", ProviderErrorClass.PERMANENT),
            (200, {"model": MODEL, "choices": []}, ProviderErrorClass.PERMANENT),
            (200, {"model": MODEL, "answers": {"is_trip": 0.5}}, ProviderErrorClass.PERMANENT),
        ],
    )
    def test_a_refusal_becomes_the_class_the_graph_routes_on(
        self, ollama: FakeOllama, status: int, body: object, expected: ProviderErrorClass
    ) -> None:
        ollama.refusal = (status, body)

        reply = OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(a_call())

        assert reply.error_class is expected
        assert reply.text is None

    def test_an_unreachable_server_is_transient(self) -> None:
        reply = OllamaSystemOneProvider(settings_for(closed_port_url())).complete(a_call())

        assert reply.error_class is ProviderErrorClass.TRANSIENT

    def test_a_server_slower_than_the_timeout_is_a_timeout(self, ollama: FakeOllama) -> None:
        ollama.delay = 1.0

        reply = OllamaSystemOneProvider(settings_for(ollama.base_url)).complete(a_call(timeout=0.2))

        assert reply.error_class is ProviderErrorClass.TIMEOUT


class TestItsConfiguration:
    def test_the_adapter_refuses_a_provider_block_with_no_base_url(self) -> None:
        with pytest.raises(WorkflowConfigurationError, match="must declare 'base_url'"):
            OllamaSystemOneProvider(settings_for(None))

    def test_the_native_api_is_derived_from_the_v1_root_or_declared(self) -> None:
        derived = OllamaSystemOneProvider(settings_for("http://127.0.0.1:11434/v1/"))
        declared = OllamaSystemOneProvider(settings_for("http://a-proxy/v1", api_base_url="http://a-host/api/"))

        assert derived.endpoint == "http://127.0.0.1:11434/v1/systemone"
        assert derived.api_base_url == "http://127.0.0.1:11434/api"
        assert declared.api_base_url == "http://a-host/api"


class TestReleasingWhatTheRunBrought:
    def test_a_model_the_run_brought_is_released_when_the_run_ends(self, ollama: FakeOllama) -> None:
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url))
        provider.complete(a_call())
        assert ollama.loaded == {MODEL}

        provider.finalize(FinalizeReason.COMPLETED)

        assert ollama.loaded == set()
        assert ollama.unloads() == [MODEL]

    @pytest.mark.parametrize("reason", [FinalizeReason.FAILED, FinalizeReason.ABORTED, FinalizeReason.RECONFIGURED])
    def test_every_outcome_but_a_pause_releases(self, ollama: FakeOllama, reason: FinalizeReason) -> None:
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url))
        provider.complete(a_call())

        provider.finalize(reason)

        assert ollama.loaded == set()

    def test_a_pause_keeps_the_model_for_the_answer_that_resumes_the_run(self, ollama: FakeOllama) -> None:
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url))
        provider.complete(a_call())

        provider.finalize(FinalizeReason.PAUSED)

        assert ollama.loaded == {MODEL}
        assert ollama.unloads() == []

    def test_a_model_the_server_held_before_the_run_is_never_released(self, ollama: FakeOllama) -> None:
        ollama.loaded.add(MODEL)
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url))
        provider.complete(a_call())

        provider.finalize(FinalizeReason.COMPLETED)

        assert ollama.loaded == {MODEL}
        assert ollama.unloads() == []

    def test_a_model_already_gone_is_not_asked_for_again(self, ollama: FakeOllama) -> None:
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url))
        provider.complete(a_call())
        ollama.loaded.clear()

        provider.finalize(FinalizeReason.COMPLETED)

        assert ollama.unloads() == []

    def test_a_name_without_a_tag_is_the_model_the_server_lists_under_latest(self, ollama: FakeOllama) -> None:
        ollama.loaded.add("a-decision-model:latest")
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url))
        provider.complete(a_call(model="a-decision-model"))

        provider.finalize(FinalizeReason.COMPLETED)

        assert ollama.unloads() == []

    def test_a_listing_that_cannot_be_read_before_the_call_claims_nothing(self, ollama: FakeOllama) -> None:
        ollama.fail_listing = 500
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url))

        reply = provider.complete(a_call())
        ollama.fail_listing = None
        provider.finalize(FinalizeReason.COMPLETED)

        assert not reply.failed
        assert ollama.unloads() == []

    def test_a_release_that_fails_is_raised_for_the_seat_to_report(self, ollama: FakeOllama) -> None:
        provider = OllamaSystemOneProvider(settings_for(ollama.base_url))
        provider.complete(a_call())
        ollama.fail_unload = 500

        with pytest.raises(OllamaResidencyError, match=MODEL):
            provider.finalize(FinalizeReason.COMPLETED)

    def test_two_blocks_on_one_server_release_each_what_it_brought_exactly_once(
        self, ollama: FakeOllama, provider_seat_guard
    ) -> None:
        install_provider_settings(
            {
                "first": settings_for(ollama.base_url, name="first"),
                "second": settings_for(ollama.base_url, name="second"),
            }
        )
        from workflow_engine.providers.provider_seat import resolve_provider

        resolve_provider("first").complete(a_call())
        resolve_provider("second").complete(a_call())
        resolve_provider("second").complete(a_call(model="another-decision-model:small"))

        failures = finalize_providers(FinalizeReason.COMPLETED)

        assert failures == {}
        assert ollama.loaded == set()
        assert sorted(ollama.unloads()) == ["a-decision-model:small", "another-decision-model:small"]


def _state(tmp_path: Path) -> StateReadOnlyView:
    state = StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="f",
        current_node_id="IS_TRIP",
        session_id="s",
    )
    state.add_parameter("message", "Please pay the invoice for trip 12345, order 55821.")
    return StateReadOnlyView.from_state(state)


class TestBehindTheLlmNode:
    """What the consumer acts on: a node that binds the probability as a value of the bus."""

    def test_a_noul_answer_binds_as_a_float_and_a_choice_as_a_dictionary(
        self, ollama: FakeOllama, tmp_path: Path, provider_seat_guard
    ) -> None:
        install_provider_settings({"decide": settings_for(ollama.base_url)})
        action = LlmAction(
            {
                "provider": "decide",
                "prompt": "${param.message}",
                "format": "json",
                "answer": [{"name": "is_trip", "type": "float"}, {"name": "kind", "type": "dict"}],
                "options": {"questions": {"is_trip": NOUL, "kind": CHOICE}},
            }
        )

        output = action.execute(_state(tmp_path), None)

        assert output.error_code is None
        assert output.param_writes["is_trip"].value == pytest.approx(0.9163)
        assert output.param_writes["kind"].value["choice"] == "pay"
        assert ollama.calls()[-1]["state"] == "Please pay the invoice for trip 12345, order 55821."
        assert output.details["usage"] == {"prompt_tokens": 174, "completion_tokens": 1}

    def test_a_refused_call_is_a_routable_error_of_the_node(
        self, ollama: FakeOllama, tmp_path: Path, provider_seat_guard
    ) -> None:
        install_provider_settings({"decide": settings_for(ollama.base_url)})
        ollama.refusal = (400, {"error": OVERFLOW_REFUSAL})
        action = LlmAction(
            {
                "provider": "decide",
                "prompt": "${param.message}",
                "format": "json",
                "answer": [{"name": "is_trip", "type": "float"}],
                "options": {"questions": {"is_trip": NOUL}},
            }
        )

        output = action.execute(_state(tmp_path), None)

        assert output.error_code == "context_overflow"
