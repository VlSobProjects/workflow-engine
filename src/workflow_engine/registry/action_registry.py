from typing import TypeVar

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.exceptions import WorkflowConfigurationError

T = TypeVar("T", bound=BaseAction)

ACTION_REGISTRY: dict[str, type[BaseAction]] = {}
ACTION_DESCRIPTIONS: dict[str, str] = {}
ACTION_NOTES: dict[str, list[str] | None] = {}


def register_action(description: str, action_type: str | None = None,notes: list[str] | None = None):
    def decorator(cls: type[T]) -> type[T]:
        key = action_type or cls.ACTION_TYPE

        if key in ACTION_REGISTRY:
            raise WorkflowConfigurationError(
                f"Action type '{key}' is already registered for class '{ACTION_REGISTRY[key].__name__}'. "
                f"Cannot register class '{cls.__name__}' for the same action type."
            )

        ACTION_REGISTRY[key] = cls
        ACTION_DESCRIPTIONS[key] = description
        ACTION_NOTES[key] = notes
        return cls

    return decorator

def get_registered_action(action_type: str) -> type[BaseAction]:
    cls = ACTION_REGISTRY.get(action_type)
    if cls is None:
        raise WorkflowConfigurationError(f"Action type '{action_type}' is not registered.")
    return cls

def create_action(action_type: str, data: dict[str, object]) -> BaseAction:
    try:
        cls = ACTION_REGISTRY[action_type]
    except KeyError as ex:
        raise WorkflowConfigurationError(f"Action type '{action_type}' is not registered.") from ex

    inst = cls(data)
    inst.validate_action()

    return inst


def get_registered_actions_info() -> dict[str, str]:
    return ACTION_DESCRIPTIONS


def get_summary_for_action(action_type: str) -> str:
    cls = ACTION_REGISTRY.get(action_type)
    if cls is None:
        raise WorkflowConfigurationError(f"Action type '{action_type}' is not registered.")
    return ACTION_DESCRIPTIONS[action_type]

def get_notes_for_action(action_type: str) -> list[str] | None:
    cls = ACTION_REGISTRY.get(action_type)
    if cls is None:
        raise WorkflowConfigurationError(f"Action type '{action_type}' is not registered.")
    return ACTION_NOTES[action_type]
