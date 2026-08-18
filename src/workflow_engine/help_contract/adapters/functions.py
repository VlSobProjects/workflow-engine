from workflow_engine.help_contract.adapters.tools import unwrap_annotation, get_function_args
from workflow_engine.help_contract.models import ComponentSource, FunctionComponent
from workflow_engine.registry.function_registry import RegisteredFunction


def adapt_function(function: RegisteredFunction, source: ComponentSource) -> FunctionComponent:
    """Adapt a function to a FunctionComponent for help contract."""
    return FunctionComponent(
        name=function.name,
        summary=function.summary if function.summary else "No summary available.",
        source=source,
        description=function.function.__doc__ if function.function.__doc__ else "No description available.",
        parameters=get_function_args(function),
        notes=None,
    )



