from __future__ import annotations

from workflow_engine.actions.base_actions import ActionWithFunction, BaseAutomaticAction
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.action_registry import register_action
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
)
from workflow_engine.tools import parameter_from_dict


@register_action()
class FunctionAction(ActionWithFunction):
    ACTION_TYPE = "function"

    def __init__(self, data: dict[str, object]):
        super().__init__(data)


@register_action()
class FunctionsAction(BaseAutomaticAction):
    ACTION_TYPE = "functions"
    function_action_list: dict[str, ActionWithFunction]
    save_to_list: str

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.save_to_list = parameter_from_dict(data, "save_to_list", str)
        f_config_dict = parameter_from_dict(data, "functions", dict)
        self.function_action_list = {
            k: FunctionAction(v) for k, v in f_config_dict.items() if isinstance(v, dict) and isinstance(k, str)
        }

    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        result: dict[str, str] = {}
        for param_name, function_action in self.function_action_list.items():
            output = function_action.execute(state, prev_output)
            if output.error_code is not None:
                result[param_name] = output.error_code
            else:
                result[param_name] = output.output_text
        if len(result) > 0:
            return ActionNodeOutput(
                output_text="Functions executed successfully",
                param_writes={self.save_to_list: ParamWrite(mode=WriteParamMode.APPEND, value=result)},
            )
        return ActionNodeOutput(
            output_text="Functions executed successfully",
            param_writes={self.save_to_list: ParamWrite(mode=WriteParamMode.APPEND, value=result)},
        )


@register_action()
class StopAction(BaseAutomaticAction):
    ACTION_TYPE = "stop"
    registered_function: RegisteredFunctionExecutor[ActionNodeOutput] | None

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.registered_function = self.get_registered_action_function(data) if FUNCTION_NAME_KEY in data else None

    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        if self.registered_function is not None:
            return self.registered_function.execute(
                parameters_modified=lambda d: d.update({"output": prev_output, "state": state})
            )
        return ActionNodeOutput(output_text=prev_output.output_text if prev_output else "")


@register_action()
class StopOnError(StopAction):
    ACTION_TYPE = "stop_on_error"
    error: str

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.error = parameter_from_dict(data, "error", str)
