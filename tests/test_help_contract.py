"""Contract and metadata quality-gate tests for the operator help contract. See ADR 009.

Coverage uses core registered components only; the external-visibility test loads a real
external module through the bootstrap loading path, because that mechanism is its subject.
"""

import json
import sys
from pathlib import Path

import pytest

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.help_contract.adapters.actions import adapt_action
from workflow_engine.help_contract.adapters.codecs import adapt_codec
from workflow_engine.help_contract.adapters.functions import adapt_function
from workflow_engine.help_contract.adapters.validators import adapt_validator
from workflow_engine.help_contract.builder import (
    build_component_payload,
    build_component_type_payload,
    build_components_payload,
    collect_help_components,
    external_names_from_report,
    find_help_component,
)
from workflow_engine.help_contract.guard_catalog import (
    GUARD_CATALOG,
    MODIFIER_KIND,
    SHORTHAND_KIND,
    find_guard_entry,
)
from workflow_engine.help_contract.models import (
    CONTRACT_VERSION,
    MISSING_METADATA_TEXT,
    ComponentSource,
    ComponentType,
)
from workflow_engine.help_contract.renderers import TextComponentRenderer, render_components_list_text
from workflow_engine.registry.action_registry import ACTION_REGISTRY
from workflow_engine.registry.function_registry import FUNCTION_REGISTRY, VALIDATOR_REGISTRY
from workflow_engine.registry.type_registry import CODEC_REGISTRY
from workflow_engine.transition.guards import GUARD_CLASSES

STABLE_DETAIL_KEYS = {"name", "type", "summary", "description", "parameters", "source", "notes"}
NORMALIZED_TYPE_KEYS = {"actions", "functions", "validators", "guards", "codecs"}
PARAMETER_KEYS = {"type", "description", "required"}


@pytest.fixture
def load_engine(tmp_path: Path):
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=tmp_path.as_posix()))
    return bootstrap.build_engine()


class TestContractShape:
    """The stable payload shape defined by ADR 009."""

    def test_components_payload_shape(self, load_engine):
        payload = build_components_payload()
        assert payload["contract_version"] == CONTRACT_VERSION
        components = payload["components"]
        assert set(components.keys()) == NORMALIZED_TYPE_KEYS
        for items in components.values():
            assert items
            for item in items:
                assert set(item.keys()) == {"name", "summary", "source"}
        json.dumps(payload)

    def test_component_detail_payload_shape(self, load_engine):
        list_payload = build_components_payload()
        for type_key, items in list_payload["components"].items():
            for item in items:
                detail = build_component_payload(type_key, item["name"])
                assert detail is not None
                assert detail["contract_version"] == CONTRACT_VERSION
                component = detail["component"]
                assert set(component.keys()) >= STABLE_DETAIL_KEYS
                assert component["source"] in ("core", "external")
                parameters = component["parameters"]
                assert parameters is None or isinstance(parameters, dict)
                if parameters:
                    for parameter in parameters.values():
                        assert set(parameter.keys()) == PARAMETER_KEYS
                        assert isinstance(parameter["required"], bool)
                json.dumps(detail)

    def test_action_detail_carries_node_authoring_sections(self, load_engine):
        detail = build_component_payload("actions", "function")
        assert detail is not None
        component = detail["component"]
        assert component["execution_mode"] == "automatic"
        assert component["node_template"]
        assert set(component["action_parameters"].keys()) == {"required", "optional"}
        assert component["transition_hints"]
        assert component["examples"]
        for example in component["examples"]:
            assert set(example.keys()) == {"title", "node"}

    def test_component_type_payload_shape(self, load_engine):
        for type_key in NORMALIZED_TYPE_KEYS:
            payload = build_component_type_payload(type_key)
            assert payload is not None
            assert payload["contract_version"] == CONTRACT_VERSION
            block = payload["component_type"]
            assert set(block.keys()) == {"type", "description", "components"}
            assert block["type"] == type_key
            assert block["description"]
            assert block["components"]
            for item in block["components"]:
                assert set(item.keys()) == {"name", "summary", "source"}
            json.dumps(payload)

    def test_unknown_component_is_none(self, load_engine):
        assert find_help_component("actions", "no-such-action") is None
        assert find_help_component("no-such-type", "function") is None
        assert build_component_payload("actions", "no-such-action") is None
        assert build_component_type_payload("no-such-type") is None


def _is_internal(obj: object) -> bool:
    """Internal components are the ones registered by modules of the engine package.

    The quality gate must not depend on what else the test session imported: test-local
    and external registrations share the global registries but are not internal.
    """
    return getattr(obj, "__module__", "").startswith("workflow_engine.")


class TestMetadataQualityGate:
    """Internal components must carry complete operator metadata. See ADR 009."""

    def test_actions_have_authoring_metadata(self, load_engine):
        checked = 0
        for cls in ACTION_REGISTRY.values():
            if not _is_internal(cls):
                continue
            checked += 1
            component = adapt_action(cls, ComponentSource.CORE)
            assert component.summary, f"action '{component.name}' has no summary"
            assert component.description, f"action '{component.name}' has no operator description"
            assert component.description != MISSING_METADATA_TEXT
            assert component.node_template, f"action '{component.name}' has no node template"
            assert component.examples, f"action '{component.name}' has no examples"
            for name, parameter in (component.parameters or {}).items():
                assert parameter.description, f"action '{component.name}' parameter '{name}' is undocumented"
                assert parameter.type, f"action '{component.name}' parameter '{name}' has no type"
        assert checked

    def test_functions_and_validators_are_documented(self, load_engine):
        checked = 0
        for registry, adapt in ((FUNCTION_REGISTRY, adapt_function), (VALIDATOR_REGISTRY, adapt_validator)):
            for registered in registry.values():
                if not _is_internal(registered.function):
                    continue
                checked += 1
                component = adapt(registered, ComponentSource.CORE)
                kind = component.component_type.value
                assert component.summary, f"{kind} '{component.name}' has no summary"
                assert component.description, f"{kind} '{component.name}' has no description"
                for name, parameter in (component.parameters or {}).items():
                    assert parameter.description, f"{kind} '{component.name}' parameter '{name}' is undocumented"
        assert checked

    def test_codecs_have_metadata(self, load_engine):
        checked = 0
        for cls in CODEC_REGISTRY.values():
            if not _is_internal(cls):
                continue
            checked += 1
            component = adapt_codec(cls, ComponentSource.CORE)
            assert component.summary, f"codec '{component.name}' has no summary"
            assert component.description, f"codec '{component.name}' has no description"
            assert component.python_type, f"codec '{component.name}' has no python type mapping"
        assert checked

    def test_guard_catalog_is_documented(self):
        for entry in GUARD_CATALOG:
            assert entry.summary, f"guard '{entry.name}' has no summary"
            assert entry.description, f"guard '{entry.name}' has no description"
            for name, parameter in entry.parameters.items():
                assert parameter.description, f"guard '{entry.name}' parameter '{name}' is undocumented"

    def test_guard_catalog_covers_runtime_guard_kinds(self):
        catalog_names = {entry.name for entry in GUARD_CATALOG}
        for guard_class in GUARD_CLASSES:
            primary_key = guard_class.data_keys()[0]
            assert primary_key in catalog_names, f"guard kind '{primary_key}' is missing from the catalog"
        assert find_guard_entry("reversed").kind == MODIFIER_KIND
        assert find_guard_entry("validators").kind == SHORTHAND_KIND


class TestRenderers:
    def test_text_render_of_every_component(self, load_engine):
        for components in collect_help_components().values():
            for component in components:
                text = TextComponentRenderer(component).render()
                assert component.name in text
                assert component.summary in text

    def test_text_render_of_component_list(self, load_engine):
        text = render_components_list_text(collect_help_components())
        for type_key in NORMALIZED_TYPE_KEYS:
            assert f"{type_key}:" in text


EXTERNAL_MODULE = "wf_help_contract_external_probe"

EXTERNAL_MODULE_SOURCE = """
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import register_function


@register_function
def external_probe_function(probe: str) -> ActionNodeOutput:
    return ActionNodeOutput(output_text=probe)
"""


@pytest.fixture
def external_engine(tmp_path: Path):
    (tmp_path / f"{EXTERNAL_MODULE}.py").write_text(EXTERNAL_MODULE_SOURCE)
    sys.path.insert(0, tmp_path.as_posix())
    original_functions = dict(FUNCTION_REGISTRY)
    try:
        bootstrap = Bootstrap(
            WorkflowEngineConfiguration(work_dir=tmp_path.as_posix(), external_modules=(EXTERNAL_MODULE,))
        )
        yield bootstrap.build_engine()
    finally:
        sys.path.remove(tmp_path.as_posix())
        sys.modules.pop(EXTERNAL_MODULE, None)
        FUNCTION_REGISTRY.clear()
        FUNCTION_REGISTRY.update(original_functions)


class TestExternalComponentVisibility:
    """External registrations stay visible with explicit missing-metadata reporting."""

    def test_external_function_is_reported_with_missing_metadata(self, external_engine):
        external = external_names_from_report(external_engine.components)
        assert "external_probe_function" in external[ComponentType.FUNCTION]

        component = find_help_component("functions", "external_probe_function", external)
        assert component is not None
        assert component.source is ComponentSource.EXTERNAL
        assert component.summary == MISSING_METADATA_TEXT
        assert component.description == MISSING_METADATA_TEXT

        payload = build_component_payload("functions", "external_probe_function", external)
        assert payload["component"]["source"] == "external"

    def test_core_components_stay_core_next_to_external(self, external_engine):
        external = external_names_from_report(external_engine.components)
        component = find_help_component("functions", "copy_file", external)
        assert component is not None
        assert component.source is ComponentSource.CORE
