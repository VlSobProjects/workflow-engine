from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator

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


class ForEachOutputParameterNode(BaseAutomaticAction):
    ACTION_TYPE = "for_each_node"
    output_param_name: str
    iterator: Iterator[object] | None
    iterating: bool = False

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.output_param_name = parameter_from_dict(data, "output_param_name", str)
        self.iterator = None

    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        next_value = "iterator_error"
        error_massage = ""
        if self.iterator is None:
            if prev_output is not None:
                if self.output_param_name in prev_output.param_writes:
                    iterable = prev_output.param_writes[self.output_param_name]
                    if isinstance(iterable, Iterable):
                        self.iterator = iter(iterable)
                    else:
                        error_massage = (
                            f"Output parameter '{self.output_param_name}' is not iterable. - {type(iterable).__name__}"
                        )
                else:
                    error_massage = f"Output parameter '{self.output_param_name}' not found in previous output"
            else:
                error_massage = "Previous output is None, cannot iterate over output parameter"

        if self.iterator:
            next_value = next(self.iterator, "iterator_done").__str__()
            if next_value == "iterator_done":
                self.iterator = None
                self.iterating = False

        if next_value == "iterator_error":
            return ActionNodeOutput(output_text="", error_code="iterator_error", error_msg=error_massage)

        return ActionNodeOutput(output_text=next_value)


class PopFromQueue(BaseAutomaticAction):
    ACTION_TYPE = "pop_from_queue"
    parameter_queue_name: str
    output_queue: deque | None

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.parameter_queue_name = parameter_from_dict(data, "queue_name", str)

    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        deque_obj = state.get_param(self.parameter_queue_name)
        if isinstance(deque_obj, deque):
            if len(deque_obj) > 0:
                next_value = deque_obj.popleft()
                return ActionNodeOutput(output_text=str(next_value))
            else:
                return ActionNodeOutput(output_text="queue_empty")
        else:
            return ActionNodeOutput(
                output_text="",
                error_code="queue_not_found",
                error_msg=f"Queue '{self.parameter_queue_name}' not found or is not a deque object",
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
