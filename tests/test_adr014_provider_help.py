"""The provider component type on the operator help surface. See ADR 009 and ADR 014 §2."""

import json
from typing import cast

import pytest

from workflow_engine.cli.main import main
from workflow_engine.help_contract.builder import (
    build_component_payload,
    build_component_type_payload,
    build_components_payload,
    find_help_component,
)
from workflow_engine.help_contract.models import MISSING_METADATA_TEXT, ComponentSource, ComponentType
from workflow_engine.providers.base_provider import BaseProvider, ProviderCall, ProviderReply
from workflow_engine.providers.fake_provider import FakeProvider
from workflow_engine.registry.provider_registry import register_provider


def provider_names() -> list[str]:
    components = cast(dict[str, object], build_components_payload()["components"])
    return [cast(dict[str, str], item)["name"] for item in cast(list[object], components["providers"])]


class TestTheProviderTypeIsPublished:
    def test_the_payload_lists_providers_beside_the_other_component_types(self):
        assert FakeProvider.PROVIDER_TYPE in provider_names()

    def test_the_type_has_an_operator_description_of_its_own(self):
        payload = build_component_type_payload("providers")

        assert payload is not None
        component_type = cast(dict[str, object], payload["component_type"])
        assert "provider adapter" in cast(str, component_type["description"])
        assert cast(str, component_type["description"]).count("providers") >= 1

    def test_an_adapter_is_found_by_its_registered_name(self):
        component = find_help_component("providers", "fake")

        assert component is not None
        assert component.component_type is ComponentType.PROVIDER
        assert component.source is ComponentSource.CORE

    def test_an_unknown_adapter_name_is_a_miss_rather_than_an_error(self):
        assert find_help_component("providers", "no_such_adapter") is None


class TestWhatTheEntryTells:
    def test_the_call_options_of_an_adapter_are_its_parameters(self):
        payload = build_component_payload("providers", "fake")

        assert payload is not None
        component = cast(dict[str, object], payload["component"])
        parameters = cast(dict[str, dict[str, object]], component["parameters"])
        assert set(parameters) == {"reply", "error", "message"}
        assert all(not parameter["required"] for parameter in parameters.values())

    def test_the_entry_names_the_configuration_keys_the_adapter_reads(self):
        payload = build_component_payload("providers", "fake")

        component = cast(dict[str, object], payload["component"])
        assert component["type"] == "provider"
        assert "adapter" in cast(list[str], component["configuration_keys"])

    def test_an_adapter_from_outside_the_core_is_reported_as_external(self, provider_seat_guard):
        @register_provider(description="", provider_type="undocumented")
        class Undocumented(BaseProvider):
            def complete(self, provider_call: ProviderCall) -> ProviderReply:
                return ProviderReply.answer("")

        component = find_help_component("providers", "undocumented")

        assert component.source is ComponentSource.EXTERNAL
        assert component.summary == MISSING_METADATA_TEXT
        assert component.description == MISSING_METADATA_TEXT


class TestTheCommandAnswersForProviders:
    def test_help_component_publishes_the_adapter(self, capsys):
        with pytest.raises(SystemExit) as exit_info:
            main(["help-component", "--component-type", "providers", "--component-name", "fake", "--json"])

        assert exit_info.value.code == 0
        payload = json.loads(capsys.readouterr().out)
        component = cast(dict[str, object], cast(dict[str, object], payload["data"])["component"])
        assert component["name"] == "fake"
