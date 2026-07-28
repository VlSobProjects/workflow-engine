from __future__ import annotations

from dataclasses import dataclass

from workflow_engine.actions.base_actions import ActionWithFunction
from workflow_engine.exceptions import ActionConfigError
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.action_registry import register_action
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunction,
)


@register_action
@dataclass
class FunctionAction(ActionWithFunction):
    ACTION_TYPE = 'function'
    registered_function: RegisteredFunction
    parameters: dict[str, object] | None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> FunctionAction:
        registered_function, parameters = cls.get_registered_function(data)
        return FunctionAction(
            registered_function= registered_function,
            parameters=parameters
        )


@register_action
@dataclass
class StopAction(ActionWithFunction):
    ACTION_TYPE = 'stop'
    registered_function: RegisteredFunction | None
    parameters: dict[str, object] | None

    def execute(self, state: StateModel) -> ActionNodeOutput | None:
        if self.registered_function is not None:
            return super().execute(state)
        else:
            return None


    @classmethod
    def from_dict(cls, data: dict[str, object]) -> StopAction:
        registered_function, parameters = None, None
        if FUNCTION_NAME_KEY in data:
            registered_function, parameters = cls.get_registered_function(data)
        return StopAction(
            registered_function=registered_function,
            parameters=parameters
        )

@register_action
@dataclass
class StopOnError(StopAction):
    ACTION_TYPE = 'stop_on_error'
    error: str

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> StopOnError:
        stop = super().from_dict(data)
        err = data.get('error')
        if err is not None and isinstance(err, str):
            return StopOnError(
                registered_function=stop.registered_function,
                parameters=stop.parameters,
                error=err
            )
        else:
            raise ActionConfigError("stop_on_error action missing required field: 'error'")