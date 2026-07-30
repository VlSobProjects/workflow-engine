from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from workflow_engine.actions.base_actions import ActionWithFunction
from workflow_engine.exceptions import ActionConfigError
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.action_registry import register_action
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
)


@register_action()
@dataclass
class FunctionAction(ActionWithFunction):
    ACTION_TYPE = 'function'
    registered_function: RegisteredFunctionExecutor[ActionNodeOutput]

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> FunctionAction:
        registered_function = cls.get_registered_function(data)
        return FunctionAction(
            registered_function= registered_function,
        )



@register_action()
@dataclass
class StopAction(ActionWithFunction):
    ACTION_TYPE = 'stop'
    registered_function: RegisteredFunctionExecutor[ActionNodeOutput] | None

    def execute(self, state: StateModel) -> ActionNodeOutput | None:
        if self.registered_function is not None:
            return super().execute(state)
        else:
            return None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        registered_function = cls.get_registered_function(data) if FUNCTION_NAME_KEY in data else None            
        return cls(
            registered_function=registered_function
        )


@register_action()
@dataclass
class StopOnError(StopAction):
    ACTION_TYPE = 'stop_on_error'
    error: str

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        err = data.get('error')
        if err is not None and isinstance(err, str):
            registered_function = cls.get_registered_function(data) if FUNCTION_NAME_KEY in data else None
            return cls(
                registered_function=registered_function,
                error=err
            )
        else:
            raise ActionConfigError("stop_on_error action missing required field: 'error'")
