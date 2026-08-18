from workflow_engine.help_contract.adapters.tools import get_function_description, get_function_parameters
from workflow_engine.help_contract.models import (
    MISSING_METADATA_TEXT,
    ComponentSource,
    ValidatorComponent,
)
from workflow_engine.registry.function_registry import RegisteredValidator


def adapt_validator(validator: RegisteredValidator, source: ComponentSource) -> ValidatorComponent:
    """Adapt a registered validator into its help component: registry signature plus doc-derived text."""
    parameters, engine_provided = get_function_parameters(validator)
    description = get_function_description(validator)
    notes: list[str] = []
    if engine_provided:
        notes.append(
            f"Provided by the engine automatically, not configured: {', '.join(engine_provided)}."
        )
    if source is ComponentSource.EXTERNAL:
        description = description or MISSING_METADATA_TEXT
    return ValidatorComponent(
        name=validator.name,
        source=source,
        summary=validator.summary or (MISSING_METADATA_TEXT if source is ComponentSource.EXTERNAL else ""),
        description=description,
        parameters=parameters or None,
        notes=tuple(notes) if notes else None,
    )
