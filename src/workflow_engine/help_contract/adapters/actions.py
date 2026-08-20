from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.help_contract.models import (
    MISSING_METADATA_TEXT,
    ActionComponent,
    ComponentSource,
    HelpParameter,
)
from workflow_engine.registry.action_registry import (
    ActionOperatorMetadata,
    get_metadata_for_action,
    get_notes_for_action,
    get_summary_for_action,
)


def adapt_action(action: type[BaseAction], source: ComponentSource) -> ActionComponent:
    """Adapt a registered action into its help component.

    Detail content comes from the explicit ``ActionOperatorMetadata`` of the registration,
    never from the class docstring: operator help describes node authoring, not implementation.
    """
    action_type = action.ACTION_TYPE
    summary = get_summary_for_action(action_type)
    metadata = get_metadata_for_action(action_type)
    notes = get_notes_for_action(action_type)
    if metadata is None:
        metadata = ActionOperatorMetadata(
            description=MISSING_METADATA_TEXT if source is ComponentSource.EXTERNAL else ""
        )
    parameters: dict[str, HelpParameter] = {}
    for name, doc in metadata.required_parameters.items():
        parameters[name] = HelpParameter(
            type=doc.type, description=doc.description, required=True, template=doc.template
        )
    for name, doc in metadata.optional_parameters.items():
        parameters[name] = HelpParameter(
            type=doc.type, description=doc.description, required=False, template=doc.template
        )
    return ActionComponent(
        name=action_type,
        source=source,
        summary=summary or (MISSING_METADATA_TEXT if source is ComponentSource.EXTERNAL else ""),
        description=metadata.description,
        parameters=parameters or None,
        notes=tuple(notes) if notes else None,
        execution_mode=action.execution_mode().name.lower(),
        node_template=dict(metadata.node_template),
        action_parameters={
            "required": list(metadata.required_parameters),
            "optional": list(metadata.optional_parameters),
        },
        transition_hints=tuple(metadata.transition_hints),
        examples=tuple({"title": example.title, "node": example.node} for example in metadata.examples),
    )
