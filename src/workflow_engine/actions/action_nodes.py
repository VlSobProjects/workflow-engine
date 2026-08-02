from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import cast

from workflow_engine.actions.base_actions import ActionWithFunction, BaseAutomaticAction
from workflow_engine.exceptions import ActionConfigError
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.action_registry import register_action
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
)


@register_action()
class FunctionAction(ActionWithFunction):
    ACTION_TYPE = "function"

    def __init__(self, data: dict[str, object]):
        super().__init__(data)


class FunctionsAction(BaseAutomaticAction):
    ACTION_TYPE = "functions"
    function_action_list: dict[str, ActionWithFunction]
    save_to_list: str

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        if "save_to_list" in data:
            param = data["save_to_list"]
            if isinstance(param, str):
                self.save_to_list = param
            else:
                raise ActionConfigError(
                    f"FunctionsAction action 'save_to_list' must be a string, found: {param.__repr__()}"
                )
        else:
            raise ActionConfigError("FunctionsAction action missing required field: 'save_to_list'")

        if "functions" in data:
            f_config_dict = data["functions"]
            if isinstance(f_config_dict, dict):
                self.function_action_list = {
                    k: FunctionAction(v) for k, v in f_config_dict.items() if isinstance(v, dict) and isinstance(k, str)
                }
            else:
                raise ActionConfigError(
                    f"FunctionsAction action missing required 'functions' it is not a dict. expected dict with 'param_name': function dict , found : {f_config_dict.__repr__()}"
                )
        else:
            raise ActionConfigError("FunctionsAction functions action missing required field: 'functions'")

    def _execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        result: dict[str, str] = {}
        for param_name, function_action in self.function_action_list.items():
            output = function_action.execute(state, prev_output)
            if output.error_code is not None:
                result[param_name] = output.error_code
            else:
                result[param_name] = output.output_text
        results = state.get_param(self.save_to_list, list)
        if results is None:
            results = []
            state.add_parameter(self.save_to_list, results)
        results.append(result)
        return ActionNodeOutput(output_text="Functions executed successfully")


@register_action()
class CreateArtifactAction(BaseAutomaticAction):
    ACTION_TYPE = "create_artifact"
    artifact_file: str

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        artifact_file = data.get("artifact_file")
        if artifact_file is not None and isinstance(artifact_file, str):
            self.artifact_file = artifact_file
        else:
            raise ActionConfigError("create_artifact action missing required field: 'artifact_file'")

    def _execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        file_name = cast(str, state.set_parameters({"artifact_file": self.artifact_file})["artifact_file"])
        if file_name is not None and len(file_name) > 0:
            artifacts = Path(state.work_dir) / "artifacts"
            try:
                if not artifacts.is_dir():
                    artifacts.mkdir(parents=True, exist_ok=True)
                artifact_file = artifacts / file_name
                artifact_file.touch(exist_ok=True)
                return ActionNodeOutput(str(artifact_file.absolute()))
            except OSError as e:
                return ActionNodeOutput(
                    output_text=f"Exception in create artifact: {file_name}",
                    error_code="create_artifact_error",
                    error_message=f"Error creating artifact file: {e}",
                )
        else:
            return ActionNodeOutput(
                output_text=f"Invalid artifact file name: {file_name}",
                error_code="invalid_artifact_file_name",
                error_message=f"Artifact file name is invalid or empty: {file_name}",
            )


class CreateArtifactActionWithContent(CreateArtifactAction, ActionWithFunction):
    def __init__(self, data: dict[str, object]):
        super().__init__(data)

    def _execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        output = super().execute(state, prev_output)
        if output.error_code is None:
            if self.registered_function is not None:
                f_output = self.registered_function.execute(
                    parameters_modified=state.set_parameters_with_updater({"output": output, "state": state})
                )
                if f_output is not None and f_output.error_code is None and len(f_output.output_text) > 0:
                    try:
                        with open(output.output_text, "w") as f:
                            f.write(f_output.output_text)
                    except OSError as e:
                        return ActionNodeOutput(
                            output_text=f"Exception in writing to file: {output.output_text}",
                            error_code="write_artifact_error",
                            error_message=f"Error writing to artifact file: {e}",
                        )

                    return ActionNodeOutput(output_text=output.output_text)
                else:
                    return ActionNodeOutput(
                        output_text=f"Error in registered function execution: {f_output.error_message if f_output else 'No output'}",
                        error_code="registered_function_error",
                        error_message=f"Error executing registered function :{self.registered_function} for CreateArtifactActionWithContent",
                    )
            else:
                return ActionNodeOutput(
                    output_text="No registered function provided for CreateArtifactActionWithContent",
                    error_code="no_registered_function",
                    error_message="No registered function provided for CreateArtifactActionWithContent",
                )
        else:
            return output


@register_action()
class ForEachOutputParameterNode(BaseAutomaticAction):
    ACTION_TYPE = "for_each_node"
    output_param_name: str
    iterator: Iterator[object] | None
    iterating: bool = False

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        output_param_name = data.get("output_param_name")
        if output_param_name is not None and isinstance(output_param_name, str):
            self.output_param_name = output_param_name
        else:
            raise ActionConfigError(
                "for_each_node action missing required field: 'output_param_name' or it is not a string"
            )
        self.iterator = None

    def _execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        next_value = "iterator_error"
        error_massage = ""
        if self.iterator is None:
            if prev_output is not None:
                if self.output_param_name in prev_output.parameters:
                    iterable = prev_output.parameters[self.output_param_name]
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
            return ActionNodeOutput(output_text="", error_code="iterator_error", error_message=error_massage)

        return ActionNodeOutput(output_text=next_value)


class PopFromQueue(BaseAutomaticAction):
    ACTION_TYPE = "pop_from_queue"
    parameter_queue_name: str
    output_queue: deque | None

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        queue_name = data.get("queue_name")
        if queue_name is not None and isinstance(queue_name, str):
            self.parameter_queue_name = queue_name
        else:
            raise ActionConfigError("pop_from_queue action missing required field: 'queue_name' or it is not a string")

    def _execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
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
                error_message=f"Queue '{self.parameter_queue_name}' not found or is not a deque object",
            )


@register_action()
class StopAction(BaseAutomaticAction):
    ACTION_TYPE = "stop"
    registered_function: RegisteredFunctionExecutor[ActionNodeOutput] | None

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.registered_function = self.get_registered_function(data) if FUNCTION_NAME_KEY in data else None

    def _execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput | None:
        if self.registered_function is not None:
            return self.registered_function.execute(
                parameters_modified=state.set_parameters_with_updater({"output": prev_output, "state": state})
            )
        else:
            return None


@register_action()
class StopOnError(StopAction):
    ACTION_TYPE = "stop_on_error"
    error: str

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        error = data.get("error")
        if error is not None and isinstance(error, str):
            self.error = error
        else:
            raise ActionConfigError("stop_on_error action missing required field: 'error'")
