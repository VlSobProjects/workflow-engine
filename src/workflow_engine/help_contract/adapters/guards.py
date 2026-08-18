from workflow_engine.help_contract.adapters.tools import get_function_args
from workflow_engine.help_contract.models import ComponentSource, ValidationComponent, GuardComponent
from workflow_engine.registry.function_registry import RegisteredValidator
from workflow_engine.transition.guards import BaseGuard, GroupGuard


def adapt_validation(function: RegisteredValidator, source: ComponentSource) -> ValidationComponent:
    """Adapt a function to a ValidationComponent for help contract."""
    return ValidationComponent(
        name=function.name,
        summary=function.summary if function.summary else "No summary available.",
        source=source,
        description=function.function.__doc__ if function.function.__doc__ else "No description available.",
        parameters=get_function_args(function),
        notes=None,
    )

def _get_gard_parameters(guard_type:type[BaseGuard]) -> dict[str, tuple[type, str]]:
    parameters = {}
    for k in guard_type.data_keys():
        if issubclass(guard_type, GroupGuard):
            parameters[k] = list, "list of the dictionaries with guard parameters"
        else:
            parameters[k] = str, "value of the guard parameter"

    return parameters



def adapt_guard(guard_type:type[BaseGuard], source: ComponentSource) -> GuardComponent:
    """Adapt a guard to a GuardComponent for help contract."""
    return GuardComponent(
        name=guard_type.__name__,
        summary=guard_type.__doc__ if guard_type.__doc__ else "No description available.",
        source=source,
        description=guard_type.__doc__ if guard_type.__doc__ else "No description available.",
        parameters=_get_gard_parameters(guard_type),
        notes=None,
    )
