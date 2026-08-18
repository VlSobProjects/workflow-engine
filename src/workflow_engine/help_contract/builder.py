from workflow_engine.help_contract.adapters.actions import adapt_action
from workflow_engine.help_contract.adapters.codecs import adapt_codec
from workflow_engine.help_contract.adapters.functions import adapt_function
from workflow_engine.help_contract.adapters.guards import adapt_validation, adapt_guard
from workflow_engine.help_contract.models import ComponentSource, HelpComponent, ComponentType
from workflow_engine.registry.action_registry import ACTION_REGISTRY
from workflow_engine.registry.function_registry import FUNCTION_REGISTRY, VALIDATOR_REGISTRY
from workflow_engine.registry.type_registry import CODEC_REGISTRY
from workflow_engine.transition.guards import GUARD_CLASSES


def get_all_help_component(source:ComponentSource) -> dict[ComponentType,list[HelpComponent]]:
    components: dict[ComponentType,list[HelpComponent]] = {}
    for c_type in ComponentType:
        match c_type:
            case ComponentType.ACTION:
                components[c_type] = [adapt_action(c, source=source) for c in ACTION_REGISTRY.values()]
            case ComponentType.FUNCTION:
                components[c_type] = [adapt_function(f, source=source) for f in FUNCTION_REGISTRY.values()]
            case ComponentType.VALIDATION_FUNCTION:
                components[c_type] = [adapt_validation(f, source=source) for f in VALIDATOR_REGISTRY.values()]
            case ComponentType.CODEC:
                components[c_type] = [adapt_codec(c, source=source) for c in CODEC_REGISTRY.values()]
            case ComponentType.GUARD:
                components[c_type] = [adapt_guard(c, source=source) for c in GUARD_CLASSES]


    return components
