"""The provider-adapter package and its `openai_compatible` adapter. See ADR 014 §2.

Nothing here reaches a network. The adapter speaks HTTP, so it is tested against HTTP: a scripted
server on a loopback port answers whatever the test tells it to, which is the only way to prove that
a status code becomes the error class the graph routes on. The one real model server this package is
written for is reached by hand, not by pytest.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import MappingProxyType

import pytest

from workflow_engine.bootstrap.component_loader import ComponentLoader
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.providers.base_provider import ProviderCall, ProviderErrorClass, ProviderSettings
from workflow_engine.registry import provider_registry
from workflow_engine.registry.provider_registry import get_registered_provider
from workflow_engine_providers.lmstudio import ADAPTER_NAME as LMSTUDIO_ADAPTER_NAME
from workflow_engine_providers.openai_compatible import (
    ADAPTER_NAME,
    DEFAULT_TIMEOUT_SECONDS,
    OpenAICompatibleProvider,
)

PACKAGE_NAME = "workflow_engine_providers"
PACKAGE_ADAPTERS = (ADAPTER_NAME, LMSTUDIO_ADAPTER_NAME)
EXAMPLE_CONFIG = Path(__file__).resolve().parents[1] / "src" / PACKAGE_NAME / "example_config.json"


def completion(content: str, model: str = "served-model", usage: dict[str, object] | None = None) -> dict[str, object]:
    """A chat completion response in the shape every server speaking this protocol returns."""
    body: dict[str, object] = {"model": model, "choices": [{"message": {"role": "assistant", "content": content}}]}
    if usage is not None:
        body["usage"] = usage
    return body


@dataclass
class ReceivedRequest:
    path: str
    headers: dict[str, str]
    body: dict[str, object]


@dataclass
class Script:
    status: int = 200
    body: object = field(default_factory=lambda: completion("scripted"))
    delay: float = 0.0


class _ScriptedHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_POST(self) -> None:
        """Record what the adapter sent, then answer whatever the test scripted."""
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        self.server.received.append(ReceivedRequest(self.path, dict(self.headers), json.loads(raw)))
        script = self.server.script
        if script.delay:
            time.sleep(script.delay)
        payload = script.body if isinstance(script.body, str) else json.dumps(script.body)
        encoded = payload.encode("utf-8")
        self.send_response(script.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output free of the server's access log."""
        return


class ScriptedServer(ThreadingHTTPServer):
    """A loopback server that answers one scripted response and records what it was sent."""

    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _ScriptedHandler)
        self.received: list[ReceivedRequest] = []
        self.script = Script()

    @property
    def base_url(self) -> str:
        host, port = self.server_address[0], self.server_address[1]
        return f"http://{host}:{port}/v1"

    def answers(self, status: int = 200, body: object | None = None, delay: float = 0.0) -> None:
        self.script = Script(status=status, body=completion("scripted") if body is None else body, delay=delay)

    @property
    def last(self) -> ReceivedRequest:
        assert self.received, "the adapter sent no request"
        return self.received[-1]


@pytest.fixture
def server() -> Iterator[ScriptedServer]:
    scripted = ScriptedServer()
    thread = threading.Thread(target=scripted.serve_forever, daemon=True)
    thread.start()
    yield scripted
    scripted.shutdown()
    scripted.server_close()
    thread.join(timeout=5)


def settings_for(base_url: str | None, **overrides: object) -> ProviderSettings:
    fields: dict[str, object] = {
        "name": "local",
        "adapter": ADAPTER_NAME,
        "base_url": base_url,
        "model": "configured-model",
    }
    fields.update(overrides)
    if "options" in fields:
        fields["options"] = MappingProxyType(dict(fields["options"]))
    return ProviderSettings(**fields)


def a_call(prompt: str = "How many files?", model: str = "asked-model", **options: object) -> ProviderCall:
    return ProviderCall(prompt=prompt, model=model, options=MappingProxyType(dict(options)))


def closed_port_url() -> str:
    """A loopback address with nothing behind it, so the connection is refused at once."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}/v1"


class TestTheRequestItSends:
    def test_the_prompt_travels_as_a_single_user_message_to_the_chat_endpoint(self, server: ScriptedServer) -> None:
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        provider.complete(a_call(prompt="Name the file."))

        assert server.last.path == "/v1/chat/completions"
        assert server.last.body["messages"] == [{"role": "user", "content": "Name the file."}]
        assert server.last.body["model"] == "asked-model"

    def test_a_system_option_becomes_a_message_before_the_prompt(self, server: ScriptedServer) -> None:
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        provider.complete(a_call(prompt="Name the file.", system="Answer with one word."))

        assert server.last.body["messages"] == [
            {"role": "system", "content": "Answer with one word."},
            {"role": "user", "content": "Name the file."},
        ]

    def test_the_provider_block_supplies_a_system_message_the_node_can_override(self, server: ScriptedServer) -> None:
        provider = OpenAICompatibleProvider(settings_for(server.base_url, options={"system": "Be terse."}))

        provider.complete(a_call())
        from_block = server.last.body["messages"][0]
        provider.complete(a_call(system="Be exact."))
        from_node = server.last.body["messages"][0]

        assert from_block == {"role": "system", "content": "Be terse."}
        assert from_node == {"role": "system", "content": "Be exact."}

    def test_an_option_the_adapter_does_not_own_is_sent_to_the_server_unread(self, server: ScriptedServer) -> None:
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        provider.complete(a_call(temperature=0, max_tokens=64, a_server_specific_field={"nested": True}))

        assert server.last.body["temperature"] == 0
        assert server.last.body["max_tokens"] == 64
        assert server.last.body["a_server_specific_field"] == {"nested": True}

    def test_the_two_options_the_adapter_owns_never_reach_the_body(self, server: ScriptedServer) -> None:
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        provider.complete(a_call(timeout=30, system="Be terse."))

        assert "timeout" not in server.last.body
        assert "system" not in server.last.body

    def test_the_credential_is_read_from_the_environment_at_the_moment_of_the_call(
        self, server: ScriptedServer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = OpenAICompatibleProvider(settings_for(server.base_url, api_key_env="A_TEST_MODEL_KEY"))

        monkeypatch.setenv("A_TEST_MODEL_KEY", "first-secret")
        provider.complete(a_call())
        first = server.last.headers["Authorization"]
        monkeypatch.setenv("A_TEST_MODEL_KEY", "second-secret")
        provider.complete(a_call())
        second = server.last.headers["Authorization"]

        assert (first, second) == ("Bearer first-secret", "Bearer second-secret")

    def test_a_server_that_needs_no_credential_is_sent_none(self, server: ScriptedServer) -> None:
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        provider.complete(a_call())

        assert "Authorization" not in server.last.headers

    def test_a_base_url_with_a_trailing_slash_still_addresses_one_endpoint(self, server: ScriptedServer) -> None:
        provider = OpenAICompatibleProvider(settings_for(server.base_url + "/"))

        provider.complete(a_call())

        assert provider.endpoint.endswith("/v1/chat/completions")
        assert server.last.path == "/v1/chat/completions"


class TestTheReplyItReads:
    def test_the_content_of_the_first_choice_is_the_reply(self, server: ScriptedServer) -> None:
        server.answers(body=completion("47 files."))
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        reply = provider.complete(a_call())

        assert not reply.failed
        assert reply.text == "47 files."

    def test_the_model_the_server_reports_wins_over_the_model_that_was_asked_for(self, server: ScriptedServer) -> None:
        server.answers(body=completion("ok", model="the-one-actually-loaded"))
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        reply = provider.complete(a_call(model="asked-model"))

        assert reply.model == "the-one-actually-loaded"

    def test_a_server_that_reports_no_model_leaves_the_asked_one_in_the_audit(self, server: ScriptedServer) -> None:
        server.answers(body={"choices": [{"message": {"content": "ok"}}]})
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        reply = provider.complete(a_call(model="asked-model"))

        assert reply.model == "asked-model"

    def test_the_token_counts_are_read_into_the_usage_of_the_reply(self, server: ScriptedServer) -> None:
        server.answers(body=completion("ok", usage={"prompt_tokens": 31, "completion_tokens": 4}))
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        reply = provider.complete(a_call())

        assert reply.usage is not None
        assert reply.usage.to_dict() == {"prompt_tokens": 31, "completion_tokens": 4}

    def test_a_server_that_reports_no_counts_reports_no_usage(self, server: ScriptedServer) -> None:
        server.answers(body=completion("ok"))
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        assert provider.complete(a_call()).usage is None


class TestTheFailuresItClassifies:
    @pytest.mark.parametrize(
        ("status", "body", "expected"),
        [
            (429, {"error": "slow down"}, ProviderErrorClass.RATE_LIMITED),
            (408, {"error": "request timeout"}, ProviderErrorClass.TIMEOUT),
            (413, {"error": "payload too large"}, ProviderErrorClass.CONTEXT_OVERFLOW),
            (401, {"error": "invalid api key"}, ProviderErrorClass.PERMANENT),
            (403, {"error": "forbidden"}, ProviderErrorClass.PERMANENT),
            (404, {"error": "model not found"}, ProviderErrorClass.INVALID_REQUEST),
            (422, {"error": "unprocessable"}, ProviderErrorClass.INVALID_REQUEST),
            (400, {"error": {"code": "unknown_field"}}, ProviderErrorClass.INVALID_REQUEST),
            (500, {"error": "internal"}, ProviderErrorClass.TRANSIENT),
            (503, {"error": "loading"}, ProviderErrorClass.TRANSIENT),
        ],
    )
    def test_a_status_becomes_the_class_the_graph_routes_on(
        self, server: ScriptedServer, status: int, body: object, expected: ProviderErrorClass
    ) -> None:
        server.answers(status=status, body=body)
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        reply = provider.complete(a_call())

        assert reply.failed
        assert reply.error_class is expected

    @pytest.mark.parametrize(
        "message",
        [
            "This model's maximum context length is 4096 tokens",
            "the prompt is too long for the context window",
            "Please reduce the length of the messages",
            "context_length_exceeded",
        ],
    )
    def test_a_bad_request_that_names_the_context_is_an_overflow_and_not_an_invalid_request(
        self, server: ScriptedServer, message: str
    ) -> None:
        server.answers(status=400, body={"error": {"message": message}})
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        assert provider.complete(a_call()).error_class is ProviderErrorClass.CONTEXT_OVERFLOW

    def test_a_server_that_cannot_be_reached_is_transient(self) -> None:
        provider = OpenAICompatibleProvider(settings_for(closed_port_url()))

        reply = provider.complete(a_call())

        assert reply.error_class is ProviderErrorClass.TRANSIENT
        assert "could not be reached" in (reply.message or "")

    def test_a_server_that_does_not_answer_in_time_is_a_timeout(self, server: ScriptedServer) -> None:
        server.answers(delay=1.0)
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        reply = provider.complete(a_call(timeout=0.05))

        assert reply.error_class is ProviderErrorClass.TIMEOUT

    @pytest.mark.parametrize(
        "body",
        [
            "not json at all",
            {"choices": []},
            {"choices": [{"message": {}}]},
            {"an": "object that is not a completion"},
            ["a list"],
        ],
    )
    def test_a_body_that_is_not_a_chat_completion_is_permanent(self, server: ScriptedServer, body: object) -> None:
        server.answers(body=body)
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        reply = provider.complete(a_call())

        assert reply.failed
        assert reply.error_class is ProviderErrorClass.PERMANENT

    def test_every_failure_carries_the_model_so_the_audit_of_the_call_is_complete(self, server: ScriptedServer) -> None:
        server.answers(status=500, body={"error": "internal"})
        provider = OpenAICompatibleProvider(settings_for(server.base_url))

        assert provider.complete(a_call(model="asked-model")).model == "asked-model"

    def test_no_transport_failure_leaves_the_adapter_as_an_exception(self, server: ScriptedServer) -> None:
        """The whole point of the classes: the node routes on a value, so nothing may be raised."""
        provider = OpenAICompatibleProvider(settings_for(server.base_url))
        for status in (400, 401, 404, 413, 429, 500, 503):
            server.answers(status=status, body={"error": "scripted"})
            assert provider.complete(a_call()).failed


class TestItsConfiguration:
    def test_the_adapter_refuses_a_provider_block_with_no_base_url(self) -> None:
        with pytest.raises(WorkflowConfigurationError, match="must declare 'base_url'"):
            OpenAICompatibleProvider(settings_for(None))

    def test_the_timeout_falls_back_from_the_call_to_the_block_to_the_default(self, server: ScriptedServer) -> None:
        from_call = OpenAICompatibleProvider(settings_for(server.base_url, options={"timeout": 30}))
        from_block = OpenAICompatibleProvider(settings_for(server.base_url, options={"timeout": 30}))
        from_default = OpenAICompatibleProvider(settings_for(server.base_url))

        assert from_call._timeout(MappingProxyType({"timeout": 5})) == 5.0
        assert from_block._timeout(MappingProxyType({})) == 30.0
        assert from_default._timeout(MappingProxyType({})) == DEFAULT_TIMEOUT_SECONDS

    def test_the_shipped_example_configures_providers_this_package_can_seat(self) -> None:
        example = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))

        assert example["external_modules"] == [PACKAGE_NAME]
        for name, block in example["providers"].items():
            settings = ProviderSettings.from_dict(name, block)
            assert get_registered_provider(settings.adapter) is not None
            assert "api_key" not in json.dumps(block).lower() or block.get("api_key_env")


class TestItLoadsAsAnExternalModule:
    def test_the_package_registers_its_adapter_only_when_the_configuration_names_it(self, provider_seat_guard) -> None:
        """The package is a plugin, not a core component: a bare install must not carry it.

        The registration is an import side effect, so proving it takes unregistering the adapter and
        dropping the package from the import cache first - otherwise this test would only observe
        that some earlier test imported it. See ADR 005.
        """
        for registry in (
            provider_registry.PROVIDER_REGISTRY,
            provider_registry.PROVIDER_DESCRIPTIONS,
            provider_registry.PROVIDER_NOTES,
            provider_registry.PROVIDER_OPERATOR_METADATA,
        ):
            for adapter in PACKAGE_ADAPTERS:
                registry.pop(adapter, None)
        for module in [name for name in sys.modules if name.startswith(PACKAGE_NAME)]:
            del sys.modules[module]

        bare = ComponentLoader(WorkflowEngineConfiguration()).load_all()
        assert not set(PACKAGE_ADAPTERS) & set(bare["Core components"]["Providers"])

        configured = ComponentLoader(WorkflowEngineConfiguration(external_modules=(PACKAGE_NAME,))).load_all()
        assert set(PACKAGE_ADAPTERS) <= set(configured["External components"]["Providers"])
        assert not set(PACKAGE_ADAPTERS) & set(configured["Core components"]["Providers"])
