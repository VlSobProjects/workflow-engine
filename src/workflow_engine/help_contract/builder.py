"""Assembly of operator help payloads from registries and static catalogs. See ADR 009."""

from workflow_engine.help_contract.adapters.actions import adapt_action
from workflow_engine.help_contract.adapters.codecs import adapt_codec
from workflow_engine.help_contract.adapters.functions import adapt_function
from workflow_engine.help_contract.adapters.guards import adapt_guard
from workflow_engine.help_contract.adapters.providers import adapt_provider
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
from workflow_engine.registry.function_registry import (
    FUNCTION_REGISTRY,
    VALIDATOR_REGISTRY,
    BaseRegisteredFunction,
)
from workflow_engine.registry.provider_registry import PROVIDER_REGISTRY
from workflow_engine.registry.type_registry import CODEC_REGISTRY, find_codec_by_type_name

CORE_PACKAGE = "workflow_engine"


def _module_source(module: str | None) -> ComponentSource:
    """Where a component comes from: the engine's own package is core, every other module external.

    The loading path does not answer this. A component registered by a launcher script - the route
    README recommends first - is in the registry before the loader takes its snapshot, so the report
    would call a user's own function `core`. The module it is defined in cannot be wrong that way.
    """
    if module is not None and (module == CORE_PACKAGE or module.startswith(f"{CORE_PACKAGE}.")):
        return ComponentSource.CORE
    return ComponentSource.EXTERNAL


def _function_source(function: BaseRegisteredFunction) -> ComponentSource:
    return _module_source(getattr(function.function, "__module__", None))


def _class_source(cls: type) -> ComponentSource:
    return _module_source(getattr(cls, "__module__", None))


def collect_help_components() -> dict[ComponentType, list[HelpComponent]]:
    """All help components by type, adapted from the registries and the guard catalog."""
    return {
        ComponentType.ACTION: [adapt_action(cls, _class_source(cls)) for cls in ACTION_REGISTRY.values()],
        ComponentType.FUNCTION: [
            adapt_function(function, _function_source(function)) for function in FUNCTION_REGISTRY.values()
        ],
        ComponentType.VALIDATOR: [
            adapt_validator(validator, _function_source(validator)) for validator in VALIDATOR_REGISTRY.values()
        ],
        ComponentType.GUARD: [adapt_guard(entry) for entry in GUARD_CATALOG],
        ComponentType.CODEC: [adapt_codec(codec, _class_source(codec)) for codec in CODEC_REGISTRY.values()],
        ComponentType.PROVIDER: [
            adapt_provider(provider, _class_source(provider)) for provider in PROVIDER_REGISTRY.values()
        ],
    }


def find_help_component(type_key: str, name: str) -> HelpComponent | None:
    """One help component by its normalized type key and name, or None when unknown."""
    component_type = COMPONENT_TYPE_BY_KEY.get(type_key)
    if component_type is None:
        return None
    match component_type:
        case ComponentType.ACTION:
            cls = ACTION_REGISTRY.get(name)
            return adapt_action(cls, _class_source(cls)) if cls else None
        case ComponentType.FUNCTION:
            function = FUNCTION_REGISTRY.get(name)
            return adapt_function(function, _function_source(function)) if function else None
        case ComponentType.VALIDATOR:
            validator = VALIDATOR_REGISTRY.get(name)
            return adapt_validator(validator, _function_source(validator)) if validator else None
        case ComponentType.GUARD:
            entry = find_guard_entry(name)
            return adapt_guard(entry) if entry else None
        case ComponentType.CODEC:
            # A codec is addressed by the same rule everywhere: `--input NAME:Path=` and the shipped
            # templates use the bare class name, so help must answer it too.
            codec = find_codec_by_type_name(name)
            return adapt_codec(codec, _class_source(codec)) if codec else None
        case ComponentType.PROVIDER:
            provider = PROVIDER_REGISTRY.get(name)
            return adapt_provider(provider, _class_source(provider)) if provider else None
    return None


def build_components_payload() -> dict[str, object]:
    """The stable ``help-components`` payload: contract_version and per-type component lists."""
    components = collect_help_components()
    return {
        "contract_version": CONTRACT_VERSION,
        "components": {
            COLLECTION_KEYS[component_type]: [component.to_list_payload() for component in items]
            for component_type, items in components.items()
        },
    }


def build_component_payload(type_key: str, name: str) -> dict[str, object] | None:
    """The stable ``help-component`` payload for one component, or None when it is unknown."""
    component = find_help_component(type_key, name)
    if component is None:
        return None
    return {"contract_version": CONTRACT_VERSION, "component": component.to_payload()}


def build_component_type_payload(type_key: str) -> dict[str, object] | None:
    """The stable ``help-component`` payload for one component type, or None when the key is unknown.

    This is the type-level mode of ``help-component``: the operator description of the type and
    the list of its components, each entry in the same shape as the ``help-components`` list.
    """
    component_type = COMPONENT_TYPE_BY_KEY.get(type_key)
    if component_type is None:
        return None
    components = collect_help_components()[component_type]
    return {
        "contract_version": CONTRACT_VERSION,
        "component_type": {
            "type": type_key,
            "description": get_component_type_description(component_type),
            "components": [component.to_list_payload() for component in components],
        },
    }
