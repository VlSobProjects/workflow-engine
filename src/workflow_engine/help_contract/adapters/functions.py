from workflow_engine.help_contract.adapters.tools import get_function_description, get_function_parameters
from workflow_engine.help_contract.models import (
    MISSING_METADATA_TEXT,
    ComponentSource,
    FunctionComponent,
)
from workflow_engine.registry.function_registry import RegisteredFunction


def adapt_function(function: RegisteredFunction, source: ComponentSource) -> FunctionComponent:
    """Adapt a registered function into its help component: registry signature plus doc-derived text."""
    parameters, engine_provided = get_function_parameters(function)
    description = get_function_description(function)
    notes: list[str] = []
    if engine_provided:
        notes.append(f"Provided by the engine automatically, not configured: {', '.join(engine_provided)}.")
    if source is ComponentSource.EXTERNAL:
        description = description or MISSING_METADATA_TEXT
    return FunctionComponent(
        name=function.name,
        source=source,
        summary=function.summary or (MISSING_METADATA_TEXT if source is ComponentSource.EXTERNAL else ""),
        description=description,
        parameters=parameters or None,
        notes=tuple(notes) if notes else None,
    )
