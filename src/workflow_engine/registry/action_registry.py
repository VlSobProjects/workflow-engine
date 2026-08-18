from dataclasses import dataclass, field
from typing import TypeVar

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.exceptions import WorkflowConfigurationError

T = TypeVar("T", bound=BaseAction)


@dataclass(frozen=True)
class ActionParameterDoc:
    """Operator documentation of one node configuration parameter of an action."""

    type: str
    description: str


@dataclass(frozen=True)
class ActionExample:
    """A complete workflow node configuration example for operator help."""

    title: str
    node: dict[str, object]


@dataclass(frozen=True)
class ActionOperatorMetadata:
    """Workflow-node authoring contract of an action, shown by operator help.

    Describes how to configure a node with this action, not how the action is
    implemented. See ADR 009.
    """

    description: str
    required_parameters: dict[str, ActionParameterDoc] = field(default_factory=dict)
    optional_parameters: dict[str, ActionParameterDoc] = field(default_factory=dict)
    node_template: dict[str, object] = field(default_factory=dict)
    transition_hints: tuple[str, ...] = ()
    examples: tuple[ActionExample, ...] = ()


ACTION_REGISTRY: dict[str, type[BaseAction]] = {}
ACTION_DESCRIPTIONS: dict[str, str] = {}
ACTION_NOTES: dict[str, list[str] | None] = {}
ACTION_OPERATOR_METADATA: dict[str, ActionOperatorMetadata | None] = {}


def register_action(
    description: str,
    action_type: str | None = None,
    notes: list[str] | None = None,
    metadata: ActionOperatorMetadata | None = None,
):
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
        ACTION_OPERATOR_METADATA[key] = metadata
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


def get_metadata_for_action(action_type: str) -> ActionOperatorMetadata | None:
    cls = ACTION_REGISTRY.get(action_type)
    if cls is None:
        raise WorkflowConfigurationError(f"Action type '{action_type}' is not registered.")
    return ACTION_OPERATOR_METADATA[action_type]
