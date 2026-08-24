"""The seat of provider instances and the `providers` configuration section. See ADR 014 §2-3."""

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration, load_config_file
from workflow_engine.bootstrap.session_factory import SESSION_DIRECTORY, SESSION_FILE
from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.providers.base_provider import (
    BaseProvider,
    FinalizeReason,
    ProviderCall,
    ProviderReply,
    ProviderSettings,
)
from workflow_engine.providers.fake_provider import FakeProvider
from workflow_engine.providers.provider_seat import (
    configured_providers,
    finalize_providers,
    install_provider_settings,
    resolve_provider,
    seated_providers,
)
from workflow_engine.registry.provider_registry import register_provider


def fake_settings(name: str = "local", **overrides) -> ProviderSettings:
    fields: dict[str, object] = {"name": name, "adapter": "fake"}
    fields.update(overrides)
    return ProviderSettings(**fields)


def config_with_providers(tmp_path: Path, providers: dict[str, object]) -> Path:
    config_path = tmp_path / "workflow_engine_config.json"
    config_path.write_text(
        json.dumps({"work_dir": (tmp_path / "runtime").as_posix(), "storage": {}, "providers": providers}),
        encoding="utf-8",
    )
    return config_path


class TestTheSeat:
    def test_a_provider_name_is_seated_once_and_reused(self, provider_seat_guard):
        install_provider_settings({"local": fake_settings()})

        first = resolve_provider("local")
        second = resolve_provider("local")

        assert first is second
        assert isinstance(first, FakeProvider)
        assert seated_providers() == ("local",)

    def test_a_name_the_installation_does_not_configure_is_a_configuration_error(self, provider_seat_guard):
        install_provider_settings({"local": fake_settings()})

        with pytest.raises(WorkflowConfigurationError, match="Provider 'cloud' is not configured"):
            resolve_provider("cloud")

    def test_a_configured_block_naming_an_unregistered_adapter_fails_at_first_use(self, provider_seat_guard):
        install_provider_settings({"local": fake_settings(adapter="no_such_adapter")})

        assert configured_providers()["local"].adapter == "no_such_adapter"
        with pytest.raises(WorkflowConfigurationError, match="Provider adapter 'no_such_adapter' is not registered"):
            resolve_provider("local")

    def test_reinstalling_the_same_configuration_keeps_what_an_adapter_remembers(self, provider_seat_guard):
        install_provider_settings({"local": fake_settings()})
        seated = resolve_provider("local")
        seated.calls = 7

        install_provider_settings({"local": fake_settings()})

        assert resolve_provider("local") is seated
        assert seated.calls == 7

    def test_changed_settings_release_the_instance_built_from_the_old_ones(self, provider_seat_guard):
        install_provider_settings({"local": fake_settings(model="first-model")})
        seated = resolve_provider("local")

        install_provider_settings({"local": fake_settings(model="second-model")})

        assert seated.last_finalize_reason is FinalizeReason.RECONFIGURED
        assert seated_providers() == ()
        assert resolve_provider("local") is not seated

    def test_finalizing_tells_every_seated_adapter_why_and_unseats_it(self, provider_seat_guard):
        install_provider_settings({"local": fake_settings(), "other": fake_settings("other")})
        first = resolve_provider("local")
        second = resolve_provider("other")

        failures = finalize_providers(FinalizeReason.COMPLETED)

        assert failures == {}
        assert first.last_finalize_reason is FinalizeReason.COMPLETED
        assert second.last_finalize_reason is FinalizeReason.COMPLETED
        assert seated_providers() == ()

    def test_an_adapter_that_fails_to_release_is_reported_and_dropped(self, provider_seat_guard):
        @register_provider(description="Fails to release.", provider_type="stuck")
        class Stuck(BaseProvider):
            def complete(self, provider_call: ProviderCall) -> ProviderReply:
                return ProviderReply.answer("")

            def finalize(self, reason: FinalizeReason) -> None:
                raise RuntimeError("the model server did not answer")

        install_provider_settings({"local": fake_settings(adapter="stuck")})
        resolve_provider("local")

        failures = finalize_providers(FinalizeReason.COMPLETED)

        assert failures == {"local": "RuntimeError: the model server did not answer"}
        assert seated_providers() == ()


class TestTheConfigurationSection:
    def test_the_section_is_read_from_the_configuration_file(self, tmp_path, provider_seat_guard):
        config_path = config_with_providers(
            tmp_path,
            {
                "local": {
                    "adapter": "fake",
                    "base_url": "http://localhost:1234/v1",
                    "model": "a-model",
                    "api_key_env": "WE_TEST_PROVIDER_KEY",
                }
            },
        )

        config = load_config_file(config_path, cwd=tmp_path)

        assert config.providers["local"].adapter == "fake"
        assert config.providers["local"].model == "a-model"
        assert config.providers["local"].api_key_env == "WE_TEST_PROVIDER_KEY"

    def test_an_installation_without_the_section_configures_no_provider(self, tmp_path, provider_seat_guard):
        config = load_config_file(tmp_path / "workflow_engine_config.json", cwd=tmp_path)

        assert dict(config.providers) == {}

    def test_a_malformed_block_fails_the_load(self, tmp_path, provider_seat_guard):
        config_path = config_with_providers(tmp_path, {"local": "fake"})

        with pytest.raises(WorkflowConfigurationError, match="Provider 'local' must be an object"):
            load_config_file(config_path, cwd=tmp_path)

    def test_the_section_survives_the_round_trip_through_the_configuration_file(self, tmp_path, provider_seat_guard):
        config_path = config_with_providers(tmp_path, {"local": {"adapter": "fake", "model": "a-model"}})
        config = load_config_file(config_path, cwd=tmp_path)

        written = json.loads(json.dumps(config.to_dict()))

        assert WorkflowEngineConfiguration.from_dict(written).providers == config.providers

    def test_bootstrap_installs_the_configured_providers_into_the_seat(self, tmp_path, provider_seat_guard):
        config_path = config_with_providers(tmp_path, {"local": {"adapter": "fake", "model": "a-model"}})
        config = load_config_file(config_path, cwd=tmp_path)

        Bootstrap(config).build_engine()

        assert resolve_provider("local").settings.model == "a-model"

    def test_the_block_does_not_enter_the_session_record(self, tmp_path, provider_seat_guard):
        config_path = config_with_providers(
            tmp_path, {"local": {"adapter": "fake", "api_key_env": "WE_TEST_PROVIDER_KEY"}}
        )
        engine = Bootstrap(load_config_file(config_path, cwd=tmp_path)).build_engine()
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "flow_id": "seat-session",
                    "start_node_id": "DONE",
                    "nodes": [
                        {
                            "id": "DONE",
                            "action_type": "stop",
                            "action_parameters": {
                                "function_name": "echo_value",
                                "function_parameters": {"value": "finished"},
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        session_id = engine.init_new_session(workflow_path=workflow_path)

        record = (tmp_path / "runtime" / SESSION_DIRECTORY / session_id / SESSION_FILE).read_text(encoding="utf-8")

        assert "provider" not in record
        assert "WE_TEST_PROVIDER_KEY" not in record


class TestTheSeatIsReachableWithoutTheEngine:
    def test_a_registered_function_can_reach_the_instance_the_run_uses(self, provider_seat_guard):
        """The channel a local adapter's own release function takes. See ADR 014 §2."""
        install_provider_settings({"local": fake_settings(options=MappingProxyType({"replies": ["scripted"]}))})
        seated = resolve_provider("local")
        seated.complete(ProviderCall(prompt="p", model="m"))

        reached = resolve_provider("local")

        assert reached is seated
        assert reached.calls == 1
