"""The `lmstudio` adapter: model residency around the inherited call. See ADR 014 §2.

The server these tests run against keeps real residency - a load adds an instance, an unload removes
one, and the listing reports what it holds. That is the point: the ownership rule and the release
policy are then measured by asking the server what is loaded, rather than by counting the requests
the adapter made, so a test fails when the model is left in memory rather than when an internal call
stopped happening.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import MappingProxyType

import pytest

from workflow_engine.providers.base_provider import (
    FinalizeReason,
    ProviderCall,
    ProviderErrorClass,
    ProviderSettings,
)
from workflow_engine.providers.provider_seat import (
    finalize_providers,
    install_provider_settings,
    resolve_provider,
)
from workflow_engine_providers.lmstudio import (
    ADAPTER_NAME,
    LOAD_FAILED_TYPE,
    RELEASE_FOREIGN_OPTION,
    RELEASE_OPTION,
    LmStudioProvider,
    LmStudioResidencyError,
)

INSTALLED_MODEL = "a-publisher/a-small-model"
ANOTHER_MODEL = "a-publisher/another-model"


def completion(content: str = "an answer") -> dict[str, object]:
    return {"model": INSTALLED_MODEL, "choices": [{"message": {"role": "assistant", "content": content}}]}


@dataclass
class Failure:
    """A scripted refusal of one native endpoint, so a failing server can be measured too."""

    status: int
    body: dict[str, object] = field(default_factory=lambda: {"error": {"message": "scripted refusal"}})


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def _respond(self, status: int, payload: object) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_GET(self) -> None:
        """The model listing, reporting for each installed model what the server holds of it."""
        self.server.requests.append(("GET", self.path, {}))
        if self.path != "/api/v1/models":
            self._respond(404, {"error": {"message": "no such path"}})
            return
        self._respond(
            200,
            {
                "models": [
                    {
                        "key": key,
                        "loaded_instances": [
                            {"id": instance} for instance, model in self.server.loaded.items() if model == key
                        ],
                    }
                    for key in self.server.installed
                ]
            },
        )

    def do_POST(self) -> None:
        body = self._body()
        self.server.requests.append(("POST", self.path, body))
        if self.path == "/v1/chat/completions":
            self._respond(200, completion())
        elif self.path == "/api/v1/models/load":
            self._load(body)
        elif self.path == "/api/v1/models/unload":
            self._unload(body)
        else:
            self._respond(404, {"error": {"message": "no such path"}})

    def _load(self, body: dict[str, object]) -> None:
        if self.server.fail_load is not None:
            self._respond(self.server.fail_load.status, self.server.fail_load.body)
            return
        model = body.get("model")
        if model not in self.server.installed:
            self._respond(404, {"error": {"type": "model_not_found", "message": f"{model} not downloaded"}})
            return
        self.server.loaded[str(model)] = str(model)
        self._respond(200, {"instance_id": model, "status": "loaded"})

    def _unload(self, body: dict[str, object]) -> None:
        if self.server.fail_unload is not None:
            self._respond(self.server.fail_unload.status, self.server.fail_unload.body)
            return
        instance = str(body.get("instance_id"))
        if instance not in self.server.loaded:
            self._respond(404, {"error": {"type": "model_not_found", "message": "not loaded"}})
            return
        del self.server.loaded[instance]
        self._respond(200, {"instance_id": instance})

    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output free of the server's access log."""
        return


class FakeLmStudio(ThreadingHTTPServer):
    """A server that actually holds models: what is loaded is state, not a scripted answer."""

    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.installed: list[str] = [INSTALLED_MODEL, ANOTHER_MODEL]
        self.loaded: dict[str, str] = {}
        self.requests: list[tuple[str, str, dict[str, object]]] = []
        self.fail_load: Failure | None = None
        self.fail_unload: Failure | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.server_address[0]}:{self.server_address[1]}/v1"

    def load_from_elsewhere(self, model: str, instance: str | None = None) -> None:
        """A model put into memory by someone who is not this adapter: the application, or a peer."""
        self.loaded[instance or model] = model

    @property
    def paths(self) -> list[str]:
        return [path for _, path, _ in self.requests]


@pytest.fixture
def lms() -> Iterator[FakeLmStudio]:
    server = FakeLmStudio()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def settings_for(server: FakeLmStudio, **options: object) -> ProviderSettings:
    return ProviderSettings(
        name="local",
        adapter=ADAPTER_NAME,
        base_url=server.base_url,
        model=INSTALLED_MODEL,
        options=MappingProxyType(dict(options)),
    )


def a_call(model: str = INSTALLED_MODEL, **options: object) -> ProviderCall:
    return ProviderCall(prompt="Classify it.", model=model, options=MappingProxyType(dict(options)))


class TestFindingTheNativeApi:
    def test_the_model_api_is_derived_from_the_chat_endpoint(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))

        assert provider.api_base_url == lms.base_url.removesuffix("/v1") + "/api/v1"
        assert provider.endpoint.endswith("/v1/chat/completions")

    def test_a_declared_model_api_wins_over_the_derivation(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms, api_base_url="http://elsewhere.invalid/native/"))

        assert provider.api_base_url == "http://elsewhere.invalid/native"


class TestLoadingBeforeTheCall:
    def test_a_model_the_server_does_not_hold_is_loaded_and_then_called(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))

        reply = provider.complete(a_call())

        assert not reply.failed
        assert lms.loaded == {INSTALLED_MODEL: INSTALLED_MODEL}
        assert "/api/v1/models/load" in lms.paths
        assert "/v1/chat/completions" in lms.paths

    def test_a_model_the_server_already_holds_is_not_loaded_again(self, lms: FakeLmStudio) -> None:
        lms.load_from_elsewhere(INSTALLED_MODEL)
        provider = LmStudioProvider(settings_for(lms))

        provider.complete(a_call())

        assert "/api/v1/models/load" not in lms.paths
        assert provider.loaded_by_this_adapter == frozenset()

    def test_an_instance_is_addressed_by_its_own_name_and_not_by_the_model_s(self, lms: FakeLmStudio) -> None:
        """A server may hold several instances of one model and names them apart, as the real one does.

        The adapter must carry the instance name the listing gave it rather than reconstructing one
        from the model, or a release would address something that does not exist.
        """
        lms.load_from_elsewhere(INSTALLED_MODEL, instance=f"{INSTALLED_MODEL}:2")
        provider = LmStudioProvider(settings_for(lms, **{RELEASE_FOREIGN_OPTION: True}))

        provider.complete(a_call(**{RELEASE_OPTION: True}))

        assert lms.loaded == {}
        assert any(
            body.get("instance_id") == f"{INSTALLED_MODEL}:2"
            for _, path, body in lms.requests
            if path == "/api/v1/models/unload"
        )

    def test_the_adapter_claims_only_what_it_loaded_itself(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))

        provider.complete(a_call())

        assert provider.loaded_by_this_adapter == frozenset({INSTALLED_MODEL})


class TestReleasingAfterOneCall:
    def test_a_node_that_asks_for_the_memory_back_gets_it(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))

        reply = provider.complete(a_call(**{RELEASE_OPTION: True}))

        assert not reply.failed
        assert lms.loaded == {}
        assert provider.loaded_by_this_adapter == frozenset()

    def test_a_call_that_does_not_ask_leaves_the_model_resident(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))

        provider.complete(a_call())

        assert lms.loaded == {INSTALLED_MODEL: INSTALLED_MODEL}

    def test_a_model_the_adapter_did_not_load_survives_the_release(self, lms: FakeLmStudio) -> None:
        """A run does not evict what it did not put there: the operator's model stays loaded."""
        lms.load_from_elsewhere(INSTALLED_MODEL)
        provider = LmStudioProvider(settings_for(lms))

        provider.complete(a_call(**{RELEASE_OPTION: True}))

        assert lms.loaded == {INSTALLED_MODEL: INSTALLED_MODEL}

    def test_the_operator_can_widen_the_permission_in_the_provider_block(self, lms: FakeLmStudio) -> None:
        lms.load_from_elsewhere(INSTALLED_MODEL)
        provider = LmStudioProvider(settings_for(lms, **{RELEASE_FOREIGN_OPTION: True}))

        provider.complete(a_call(**{RELEASE_OPTION: True}))

        assert lms.loaded == {}

    def test_a_release_that_fails_does_not_fail_an_answered_call(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))
        lms.fail_unload = Failure(500)

        reply = provider.complete(a_call(**{RELEASE_OPTION: True}))

        assert not reply.failed
        assert reply.text == "an answer"

    def test_the_release_happens_even_when_the_call_was_refused(self, lms: FakeLmStudio) -> None:
        """A node that asked for the memory back asked for it whether or not the model answered."""
        provider = LmStudioProvider(settings_for(lms))
        provider.endpoint = provider.endpoint.replace("/chat/completions", "/nowhere")

        reply = provider.complete(a_call(**{RELEASE_OPTION: True}))

        assert reply.failed
        assert lms.loaded == {}


class TestReleasingWhenTheRunEnds:
    @pytest.mark.parametrize(
        "reason",
        [FinalizeReason.COMPLETED, FinalizeReason.FAILED, FinalizeReason.ABORTED, FinalizeReason.RECONFIGURED],
    )
    def test_an_outcome_that_ends_the_run_releases_what_the_adapter_loaded(
        self, lms: FakeLmStudio, reason: FinalizeReason
    ) -> None:
        provider = LmStudioProvider(settings_for(lms))
        provider.complete(a_call())

        provider.finalize(reason)

        assert lms.loaded == {}

    def test_a_pause_keeps_the_model_because_the_next_call_is_expected_shortly(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))
        provider.complete(a_call())

        provider.finalize(FinalizeReason.PAUSED)

        assert lms.loaded == {INSTALLED_MODEL: INSTALLED_MODEL}

    def test_a_model_loaded_from_elsewhere_survives_the_end_of_the_run(self, lms: FakeLmStudio) -> None:
        lms.load_from_elsewhere(ANOTHER_MODEL)
        provider = LmStudioProvider(settings_for(lms))
        provider.complete(a_call())

        provider.finalize(FinalizeReason.COMPLETED)

        assert lms.loaded == {ANOTHER_MODEL: ANOTHER_MODEL}

    def test_an_adapter_that_loaded_nothing_finalizes_quietly(self, lms: FakeLmStudio) -> None:
        LmStudioProvider(settings_for(lms)).finalize(FinalizeReason.COMPLETED)

        assert lms.loaded == {}


class TestTheMemoryIsNotTheTruth:
    def test_an_instance_someone_else_unloaded_is_not_a_failure_to_release(self, lms: FakeLmStudio) -> None:
        """The cache is of a fact outside the process, so the server is right when the two disagree."""
        provider = LmStudioProvider(settings_for(lms))
        provider.complete(a_call())
        lms.loaded.clear()

        provider.finalize(FinalizeReason.COMPLETED)

        assert provider.loaded_by_this_adapter == frozenset()

    def test_the_release_after_a_call_asks_the_server_rather_than_the_memory(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))
        provider.complete(a_call())
        lms.requests.clear()

        provider.complete(a_call(**{RELEASE_OPTION: True}))

        assert lms.paths.count("/api/v1/models") >= 1


class TestFailuresOfTheModelApi:
    def test_a_model_the_server_does_not_have_is_a_routable_failure_and_no_call_is_made(
        self, lms: FakeLmStudio
    ) -> None:
        provider = LmStudioProvider(settings_for(lms))

        reply = provider.complete(a_call(model="nobody/such-model"))

        assert reply.error_class is ProviderErrorClass.INVALID_REQUEST
        assert "/v1/chat/completions" not in lms.paths

    def test_a_load_the_server_refuses_keeps_the_class_its_status_deserves(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))
        lms.fail_load = Failure(503)

        assert provider.complete(a_call()).error_class is ProviderErrorClass.TRANSIENT

    def test_a_server_that_cannot_be_reached_is_transient_and_not_an_exception(self, lms: FakeLmStudio) -> None:
        settings = settings_for(lms)
        provider = LmStudioProvider(settings)
        provider.api_base_url = "http://127.0.0.1:1/api/v1"

        reply = provider.complete(a_call())

        assert reply.error_class is ProviderErrorClass.TRANSIENT
        assert "could not be reached" in (reply.message or "")

    @pytest.mark.parametrize(
        ("label", "message"),
        [
            (
                "predicted before allocating",
                "Model loading was stopped due to insufficient system resources. Under the current "
                "settings, this model requires approximately 44.87 GB of memory, and continuing to "
                "load it would likely overload your system and cause it to freeze.",
            ),
            (
                "discovered while allocating",
                "Failed to load LLM 'a-publisher/a-small-model': Error: Failed to load model.",
            ),
        ],
    )
    def test_a_machine_too_small_for_the_model_is_transient_in_both_wordings(
        self, lms: FakeLmStudio, label: str, message: str
    ) -> None:
        """Both messages are a real server's, for the same condition, measured in this session.

        The server refuses one way when it can predict the requirement and another way when it only
        finds out while allocating, and the second names no cause at all. A rule that read the
        wording would call that one permanent and strand a run that could have retried once memory
        came free, so the status decides and both stay retryable.
        """
        lms.fail_load = Failure(500, {"error": {"type": LOAD_FAILED_TYPE, "message": message}})
        provider = LmStudioProvider(settings_for(lms))

        assert provider.complete(a_call()).error_class is ProviderErrorClass.TRANSIENT

    def test_a_load_that_answers_without_an_instance_is_permanent(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))
        lms.fail_load = Failure(200, {"status": "loaded"})

        assert provider.complete(a_call()).error_class is ProviderErrorClass.PERMANENT


class TestWhatTheSeatDoesWithAFailedRelease:
    def test_a_model_left_resident_is_reported_and_does_not_raise_out_of_the_run(
        self, lms: FakeLmStudio, provider_seat_guard
    ) -> None:
        """ADR 014 §2: a failure to release is an operator's problem, never a failed workflow."""
        install_provider_settings({"local": settings_for(lms)})
        provider = resolve_provider("local")
        provider.complete(a_call())
        lms.fail_unload = Failure(500)

        failures = finalize_providers(FinalizeReason.COMPLETED)

        assert "local" in failures
        assert "could not release" in failures["local"]

    def test_the_adapter_names_the_failure_with_the_project_s_own_error(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))
        provider.complete(a_call())
        lms.fail_unload = Failure(500)

        with pytest.raises(LmStudioResidencyError, match="could not release"):
            provider.finalize(FinalizeReason.COMPLETED)


class TestWhatItInheritsUnchanged:
    def test_the_prompt_still_travels_as_a_single_user_message(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))

        provider.complete(a_call())

        chat = next(body for _, path, body in lms.requests if path == "/v1/chat/completions")
        assert chat["messages"] == [{"role": "user", "content": "Classify it."}]

    def test_the_residency_options_never_reach_the_chat_body(self, lms: FakeLmStudio) -> None:
        provider = LmStudioProvider(settings_for(lms))

        provider.complete(a_call(**{RELEASE_OPTION: True}))

        chat = next(body for _, path, body in lms.requests if path == "/v1/chat/completions")
        assert RELEASE_OPTION not in chat
