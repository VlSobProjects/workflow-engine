"""Assembly of operator help payloads from registries and static catalogs. See ADR 009."""

from collections.abc import Mapping, Set

from workflow_engine.help_contract.adapters.actions import adapt_action
from workflow_engine.help_contract.adapters.codecs import adapt_codec
from workflow_engine.help_contract.adapters.functions import adapt_function
from workflow_engine.help_contract.adapters.guards import adapt_guard
from workflow_engine.help_contract.adapters.validators import adapt_validator
from workflow_engine.help_contract.guard_catalog import GUARD_CATALOG, find_guard_entry
from workflow_engine.help_contract.models import (
    COLLECTION_KEYS,
    COMPONENT_TYPE_BY_KEY,
    CONTRACT_VERSION,
    ComponentSource,
    ComponentType,
    HelpComponent,
    get_component_type_description,
)
from workflow_engine.registry.action_registry import ACTION_REGISTRY
from workflow_engine.registry.function_registry import FUNCTION_REGISTRY, VALIDATOR_REGISTRY
from workflow_engine.registry.type_registry import CODEC_REGISTRY

type ExternalNames = Mapping[ComponentType, Set[str]]


def external_names_from_report(report: Mapping[str, Mapping[str, Mapping[str, str]]]) -> dict[ComponentType, set[str]]:
    """Derive the names of externally registered components from the component loader report."""
    section = report.get("External components", {})
    return {
        ComponentType.ACTION: set(section.get("Actions", {})),
        ComponentType.FUNCTION: set(section.get("Functions", {})),
        ComponentType.VALIDATOR: set(section.get("Validators", {})),
        ComponentType.CODEC: set(section.get("Codecs", {})),
    }


def _source(component_type: ComponentType, name: str, external: ExternalNames | None) -> ComponentSource:
    if external and name in external.get(component_type, set()):
        return ComponentSource.EXTERNAL
    return ComponentSource.CORE


def collect_help_components(external: ExternalNames | None = None) -> dict[ComponentType, list[HelpComponent]]:
    """All help components by type, adapted from the registries and the guard catalog."""
    return {
        ComponentType.ACTION: [
            adapt_action(cls, _source(ComponentType.ACTION, name, external)) for name, cls in ACTION_REGISTRY.items()
        ],
        ComponentType.FUNCTION: [
            adapt_function(function, _source(ComponentType.FUNCTION, name, external))
            for name, function in FUNCTION_REGISTRY.items()
        ],
        ComponentType.VALIDATOR: [
            adapt_validator(validator, _source(ComponentType.VALIDATOR, name, external))
            for name, validator in VALIDATOR_REGISTRY.items()
        ],
        ComponentType.GUARD: [adapt_guard(entry) for entry in GUARD_CATALOG],
        ComponentType.CODEC: [
            adapt_codec(codec, _source(ComponentType.CODEC, name, external)) for name, codec in CODEC_REGISTRY.items()
        ],
    }


def find_help_component(type_key: str, name: str, external: ExternalNames | None = None) -> HelpComponent | None:
    """One help component by its normalized type key and name, or None when unknown."""
    component_type = COMPONENT_TYPE_BY_KEY.get(type_key)
    if component_type is None:
        return None
    match component_type:
        case ComponentType.ACTION:
            cls = ACTION_REGISTRY.get(name)
            return adapt_action(cls, _source(component_type, name, external)) if cls else None
        case ComponentType.FUNCTION:
            function = FUNCTION_REGISTRY.get(name)
            return adapt_function(function, _source(component_type, name, external)) if function else None
        case ComponentType.VALIDATOR:
            validator = VALIDATOR_REGISTRY.get(name)
            return adapt_validator(validator, _source(component_type, name, external)) if validator else None
        case ComponentType.GUARD:
            entry = find_guard_entry(name)
            return adapt_guard(entry) if entry else None
        case ComponentType.CODEC:
            codec = CODEC_REGISTRY.get(name)
            return adapt_codec(codec, _source(component_type, name, external)) if codec else None
    return None


def build_components_payload(external: ExternalNames | None = None) -> dict[str, object]:
    """The stable ``help-components`` payload: contract_version and per-type component lists."""
    components = collect_help_components(external)
    return {
        "contract_version": CONTRACT_VERSION,
        "components": {
            COLLECTION_KEYS[component_type]: [component.to_list_payload() for component in items]
            for component_type, items in components.items()
        },
    }


def build_component_payload(
    type_key: str, name: str, external: ExternalNames | None = None
) -> dict[str, object] | None:
    """The stable ``help-component`` payload for one component, or None when it is unknown."""
    component = find_help_component(type_key, name, external)
    if component is None:
        return None
    return {"contract_version": CONTRACT_VERSION, "component": component.to_payload()}


def build_component_type_payload(type_key: str, external: ExternalNames | None = None) -> dict[str, object] | None:
    """The stable ``help-component`` payload for one component type, or None when the key is unknown.

    This is the type-level mode of ``help-component``: the operator description of the type and
    the list of its components, each entry in the same shape as the ``help-components`` list.
    """
    component_type = COMPONENT_TYPE_BY_KEY.get(type_key)
    if component_type is None:
        return None
    components = collect_help_components(external)[component_type]
    return {
        "contract_version": CONTRACT_VERSION,
        "component_type": {
            "type": type_key,
            "description": get_component_type_description(component_type),
            "components": [component.to_list_payload() for component in components],
        },
    }
