from __future__ import annotations

from typing import ClassVar, Annotated

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


@register_action("Executes a single registered function and returns its output.")
class FunctionAction(ActionWithFunction):
    """Executes a single registered function and returns its ActionNodeOutput"""
    ACTION_TYPE: ClassVar[str] = "function"

    def __init__(self, data: dict[str, object]):
        super().__init__(data)


@register_action("Executes multiple registered functions and returns their outputs.")
class FunctionsAction(BaseAutomaticAction):
    """Executes multiple registered functions and saves their outputs as a dictionary - each function output text with provided key to a list."""
    ACTION_TYPE: ClassVar[str] = "functions"
    functions: Annotated[
        dict[str, FunctionAction],
        """Dictionary of functions to execute. key is the parameter name to save the function output text 
        value is the function configuration parameters:"""
    ]
    save_to_list: str

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.save_to_list = parameter_from_dict(data, "save_to_list", str)
        f_config_dict = parameter_from_dict(data, "functions", dict)
        self.functions = {
            k: FunctionAction(v) for k, v in f_config_dict.items() if isinstance(v, dict) and isinstance(k, str)
        }

    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        result: dict[str, str] = {}
        for param_name, function_action in self.functions.items():
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


@register_action("Stops the workflow execution.")
class StopAction(BaseAutomaticAction):
    ACTION_TYPE: ClassVar[str] = "stop"
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


@register_action("Stops the workflow execution on error.")
class StopOnError(StopAction):
    """Stops the workflow execution on specific error_code from output.
    - If function is provided - check error code in function output.
    - if function is not provided - check error code in previous output"""
    ACTION_TYPE: ClassVar[str] = "stop_on_error"
    error_code: Annotated[str, "Error code to stop the workflow on"]

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.error_code = parameter_from_dict(data, "error_code", str)
