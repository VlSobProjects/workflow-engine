from typing import get_type_hints

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.help_contract.adapters.tools import is_class_var, unwrap_annotation
from workflow_engine.help_contract.models import ComponentSource, ActionComponent
from workflow_engine.registry.action_registry import get_summary_for_action, get_notes_for_action


def adapt_action(action: type[BaseAction], source: ComponentSource) -> ActionComponent:
    """Adapt an action to an ActionComponent for help contract."""
    return ActionComponent(
        name=action.ACTION_TYPE,
        summary=get_summary_for_action(action.ACTION_TYPE),
        source=source,
        action_type=action.execution_mode(),
        description=action.__doc__ if action.__doc__ else get_summary_for_action(action.ACTION_TYPE),
        parameters=get_action_parameters(action),
        notes=get_notes_for_action(action.ACTION_TYPE),
    )



def get_action_parameters(cls: type) -> dict[str, tuple[type, str]]:
    hints = get_type_hints(cls, include_extras=True)

    parameters: dict[str, tuple[type, str]] = {}

    for name, annotation in hints.items():
        if is_class_var(annotation):
            continue

        t,description = unwrap_annotation(annotation)

        parameters[name] = (t, description or "N/A")

    return parameters