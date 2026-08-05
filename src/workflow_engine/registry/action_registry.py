from typing import TypeVar

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.exceptions import WorkflowConfigurationError

T = TypeVar("T", bound=BaseAction)

ACTION_REGISTRY: dict[str, type[BaseAction]] = {}


def register_action(action_type: str | None = None):
    def decorator(cls: type[T]) -> type[T]:
        key = action_type or cls.ACTION_TYPE

        if key in ACTION_REGISTRY:
            raise WorkflowConfigurationError(
                f"Action type '{key}' is already registered for class '{ACTION_REGISTRY[key].__name__}'. "
                f"Cannot register class '{cls.__name__}' for the same action type."
            )

        ACTION_REGISTRY[key] = cls
        return cls

    return decorator


def create_action(action_type: str, data: dict[str, object]) -> BaseAction:
    try:
        cls = ACTION_REGISTRY[action_type]
    except KeyError as ex:
        raise WorkflowConfigurationError(f"Action type '{action_type}' is not registered.") from ex

    inst = cls(data)
    inst.validate_action()

    return inst


def get_registered_actions_info() -> dict[str, str]:
    return {key: cls.__doc__ or "" for key, cls in ACTION_REGISTRY.items()}
