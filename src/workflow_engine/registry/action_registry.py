from typing import TypeVar

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.exceptions import ActionRegistryError

T = TypeVar("T", bound=BaseAction)

ACTION_REGISTRY: dict[str, type[BaseAction]] = {}

def register_action(action_type: str | None = None):
    def decorator(cls: type[T]) -> type[T]:
        key = action_type or cls.ACTION_TYPE

        if key in ACTION_REGISTRY:
            raise ActionRegistryError(f"Action '{key}' already registered")

        ACTION_REGISTRY[key] = cls
        return cls

    return decorator

def create_action(action_type: str, data: dict[str, object]) -> BaseAction:
    try:
        cls = ACTION_REGISTRY[action_type]
    except KeyError:
        raise ActionRegistryError(f"Unknown action '{action_type}'")

    inst = cls(data)
    inst.validate_action()

    return inst

