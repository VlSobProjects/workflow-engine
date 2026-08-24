"""The adapter contract, its registry and the `fake` adapter that implements it. See ADR 014 §2, §5, §6."""

from types import MappingProxyType

import pytest

from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.providers.base_provider import (
    BaseProvider,
    FinalizeReason,
    ProviderCall,
    ProviderErrorClass,
    ProviderReply,
    ProviderSettings,
    ProviderUsage,
)
from workflow_engine.providers.fake_provider import FakeProvider
from workflow_engine.registry.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderOperatorMetadata,
    get_metadata_for_provider,
    get_registered_provider,
    get_registered_providers_info,
    register_provider,
)


def settings(**overrides) -> ProviderSettings:
    fields: dict[str, object] = {"name": "local", "adapter": "fake"}
    fields.update(overrides)
    return ProviderSettings(**fields)


def call(prompt: str = "say something", model: str = "", **options) -> ProviderCall:
    return ProviderCall(prompt=prompt, model=model, options=MappingProxyType(options))


class TestTheContract:
    def test_the_six_error_classes_are_the_ones_the_decision_names(self):
        assert {item.value for item in ProviderErrorClass} == {
            "transient",
            "rate_limited",
            "permanent",
            "invalid_request",
            "timeout",
            "context_overflow",
        }

    def test_a_reply_is_either_an_answer_or_a_classified_failure(self):
        answer = ProviderReply.answer("hello", model="m", usage=ProviderUsage(prompt_tokens=3))
        failure = ProviderReply.failure(ProviderErrorClass.TIMEOUT, "took too long", model="m")

        assert not answer.failed
        assert answer.text == "hello"
        assert failure.failed
        assert failure.error_class is ProviderErrorClass.TIMEOUT
        assert failure.text is None

    def test_the_model_of_a_call_falls_back_to_the_configured_default(self):
        provider = FakeProvider(settings(model="configured-model"))

        assert provider.resolve_model("asked-model") == "asked-model"
        assert provider.resolve_model(None) == "configured-model"

    def test_an_adapter_that_holds_nothing_needs_no_finalization_code(self):
        class Silent(BaseProvider):
            PROVIDER_TYPE = "silent"

            def complete(self, provider_call: ProviderCall) -> ProviderReply:
                return ProviderReply.answer("")

        assert Silent(settings()).finalize(FinalizeReason.COMPLETED) is None

    def test_the_credential_is_read_from_the_environment_at_call_time(self, monkeypatch):
        configured = settings(api_key_env="WE_TEST_PROVIDER_KEY")

        assert configured.credential() is None
        monkeypatch.setenv("WE_TEST_PROVIDER_KEY", "s3cret")
        assert configured.credential() == "s3cret"

    def test_the_configuration_carries_the_variable_name_and_never_the_secret(self, monkeypatch):
        monkeypatch.setenv("WE_TEST_PROVIDER_KEY", "s3cret")
        configured = settings(api_key_env="WE_TEST_PROVIDER_KEY")

        serialized = f"{configured.to_dict()}{configured!r}"

        assert "WE_TEST_PROVIDER_KEY" in serialized
        assert "s3cret" not in serialized


class TestTheSettingsBlock:
    def test_a_block_is_read_into_the_settings_of_one_provider(self):
        read = ProviderSettings.from_dict(
            "local",
            {
                "adapter": "fake",
                "base_url": "http://localhost:1234/v1",
                "model": "a-model",
                "api_key_env": "WE_TEST_PROVIDER_KEY",
                "options": {"timeout": 30},
            },
        )

        assert read.adapter == "fake"
        assert read.base_url == "http://localhost:1234/v1"
        assert read.model == "a-model"
        assert read.options["timeout"] == 30

    def test_a_block_round_trips_through_its_dict_form(self):
        original = settings(base_url="http://localhost:1234/v1", options=MappingProxyType({"timeout": 30}))

        assert ProviderSettings.from_dict("local", original.to_dict()) == original

    def test_an_unknown_key_is_refused_rather_than_ignored(self):
        with pytest.raises(WorkflowConfigurationError, match="unknown keys: modle"):
            ProviderSettings.from_dict("local", {"adapter": "fake", "modle": "a-model"})

    def test_a_block_without_an_adapter_is_refused(self):
        with pytest.raises(WorkflowConfigurationError, match="must declare 'adapter'"):
            ProviderSettings.from_dict("local", {"model": "a-model"})

    def test_a_field_of_the_wrong_shape_is_refused(self):
        with pytest.raises(WorkflowConfigurationError, match="'base_url' must be a string"):
            ProviderSettings.from_dict("local", {"adapter": "fake", "base_url": 8080})
        with pytest.raises(WorkflowConfigurationError, match="'options' must be an object"):
            ProviderSettings.from_dict("local", {"adapter": "fake", "options": "timeout=30"})


class TestTheRegistry:
    def test_an_adapter_is_registered_under_its_name_with_its_operator_metadata(self, provider_seat_guard):
        @register_provider(
            description="A test adapter.",
            provider_type="registered_here",
            metadata=ProviderOperatorMetadata(description="Long form.", configuration_keys=("adapter",)),
        )
        class Registered(BaseProvider):
            def complete(self, provider_call: ProviderCall) -> ProviderReply:
                return ProviderReply.answer("")

        assert get_registered_provider("registered_here") is Registered
        assert Registered.PROVIDER_TYPE == "registered_here"
        assert get_registered_providers_info()["registered_here"] == "A test adapter."
        assert get_metadata_for_provider("registered_here").description == "Long form."

    def test_the_same_adapter_name_cannot_be_registered_twice(self, provider_seat_guard):
        with pytest.raises(WorkflowConfigurationError, match="already registered"):

            @register_provider(description="A second fake.", provider_type="fake")
            class Second(BaseProvider):
                def complete(self, provider_call: ProviderCall) -> ProviderReply:
                    return ProviderReply.answer("")

    def test_a_class_outside_the_contract_is_refused(self, provider_seat_guard):
        with pytest.raises(WorkflowConfigurationError, match="not a BaseProvider"):

            @register_provider(description="Not an adapter.", provider_type="not_an_adapter")
            class NotAnAdapter:
                pass

    def test_an_adapter_without_a_name_is_refused(self, provider_seat_guard):
        with pytest.raises(WorkflowConfigurationError, match="declares no name"):

            @register_provider(description="Nameless.")
            class Nameless(BaseProvider):
                def complete(self, provider_call: ProviderCall) -> ProviderReply:
                    return ProviderReply.answer("")

    def test_an_unregistered_adapter_names_the_ones_that_exist(self):
        with pytest.raises(WorkflowConfigurationError, match=r"Registered adapters: .*fake"):
            get_registered_provider("no_such_adapter")

    def test_the_core_ships_the_fake_adapter(self):
        assert "fake" in PROVIDER_REGISTRY


class TestTheFakeAdapter:
    def test_with_nothing_scripted_the_reply_is_the_prompt_itself(self):
        provider = FakeProvider(settings(model="a-model"))

        reply = provider.complete(call("what the node sent"))

        assert reply.text == "what the node sent"
        assert reply.model == "a-model"

    def test_a_call_option_scripts_one_reply(self):
        provider = FakeProvider(settings())

        assert provider.complete(call(reply="scripted")).text == "scripted"

    def test_a_call_option_scripts_one_classified_failure(self):
        provider = FakeProvider(settings())

        reply = provider.complete(call(error="context_overflow", message="too long"))

        assert reply.failed
        assert reply.error_class is ProviderErrorClass.CONTEXT_OVERFLOW
        assert reply.message == "too long"

    def test_the_configured_sequence_is_consumed_one_entry_per_call(self):
        provider = FakeProvider(
            settings(
                options=MappingProxyType(
                    {"replies": ["first", {"text": "second"}, {"error": "rate_limited", "message": "slow down"}]}
                )
            )
        )

        first, second, third, fourth = (provider.complete(call("prompt")) for _ in range(4))

        assert first.text == "first"
        assert second.text == "second"
        assert third.error_class is ProviderErrorClass.RATE_LIMITED
        assert fourth.text == "prompt"

    def test_a_call_option_wins_over_the_configured_sequence(self):
        provider = FakeProvider(settings(options=MappingProxyType({"replies": ["scripted"]})))

        assert provider.complete(call(reply="from the call")).text == "from the call"

    def test_an_unknown_error_class_in_the_script_is_a_configuration_error(self):
        provider = FakeProvider(settings())

        with pytest.raises(WorkflowConfigurationError, match="unknown error class 'nonsense'"):
            provider.complete(call(error="nonsense"))

    def test_the_adapter_is_told_why_the_run_ended(self):
        provider = FakeProvider(settings())

        provider.finalize(FinalizeReason.PAUSED)

        assert provider.last_finalize_reason is FinalizeReason.PAUSED
