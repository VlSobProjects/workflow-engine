from __future__ import annotations

from typing import Annotated, ClassVar

from workflow_engine.actions.base_actions import ActionWithFunction, BaseAutomaticAction
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.action_registry import (
    ActionExample,
    ActionOperatorMetadata,
    ActionParameterDoc,
    register_action,
)
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
)
from workflow_engine.tools import parameter_from_dict

_SAVE_AS_DOC = ActionParameterDoc("str", "State parameter name to save the output text of the node under.")
_FUNCTION_NAME_DOC = ActionParameterDoc("str", "Name of a registered function to execute.")
_FUNCTION_PARAMETERS_DOC = ActionParameterDoc(
    "dict",
    "Parameters passed to the function. Values support 'param.<name>', 'output.<node_id>' and "
    "'artifact.<logical_name>' references resolved from the workflow state.",
)


@register_action(
    "Executes a single registered function and returns its output.",
    metadata=ActionOperatorMetadata(
        description=(
            "Runs one registered function and uses its result as the node output. The function is "
            "selected by 'function_name' and receives 'function_parameters'. The output text, the "
            "error code and the parameter writes of the function become the output of the node."
        ),
        required_parameters={"function_name": _FUNCTION_NAME_DOC},
        optional_parameters={
            "function_parameters": _FUNCTION_PARAMETERS_DOC,
            "save_as": _SAVE_AS_DOC,
        },
        node_template={
            "id": "<node-id>",
            "action_type": "function",
            "action_parameters": {
                "function_name": "<registered-function>",
                "function_parameters": {},
            },
            "transitions": [{"next": "<next-node-id>"}],
        },
        transition_hints=(
            "Route on success with a 'no_error' guard or on the output text with value guards.",
            "Handle failure codes of the function with an 'errors' transition.",
        ),
        examples=(
            ActionExample(
                title="Copy a file and save the target path",
                node={
                    "id": "COPY_FILE",
                    "action_type": "function",
                    "action_parameters": {
                        "function_name": "copy_file",
                        "function_parameters": {
                            "path_source": "param.source_file",
                            "path_target": "/tmp/copy.pdf",
                        },
                    },
                    "save_as": "copied_file",
                    "transitions": [{"next": "NEXT_NODE"}],
                    "validators": [{"function_name": "is_output_exist_file"}],
                },
            ),
        ),
    ),
)
class FunctionAction(ActionWithFunction):
    """Executes a single registered function and returns its ActionNodeOutput"""
    ACTION_TYPE: ClassVar[str] = "function"

    def __init__(self, data: dict[str, object]):
        super().__init__(data)


@register_action(
    "Executes multiple registered functions and appends their outputs to a list parameter.",
    metadata=ActionOperatorMetadata(
        description=(
            "Runs several registered functions in one node. Each entry of 'functions' maps a result "
            "key to a function configuration ('function_name' plus 'function_parameters'). The "
            "output texts are collected into one dictionary under those keys, and the dictionary is "
            "appended to the list state parameter named by 'save_to_list'. When a function fails, "
            "its error code is stored under its key instead of the output text."
        ),
        required_parameters={
            "functions": ActionParameterDoc(
                "dict",
                "Result key to function configuration. Each configuration holds 'function_name' "
                "and optional 'function_parameters', like the 'function' action.",
            ),
            "save_to_list": ActionParameterDoc(
                "str", "Name of the list state parameter the result dictionary is appended to."
            ),
        },
        optional_parameters={"save_as": _SAVE_AS_DOC},
        node_template={
            "id": "<node-id>",
            "action_type": "functions",
            "action_parameters": {
                "functions": {
                    "<result-key>": {
                        "function_name": "<registered-function>",
                        "function_parameters": {},
                    }
                },
                "save_to_list": "<list-parameter>",
            },
            "transitions": [{"next": "<next-node-id>"}],
        },
        transition_hints=(
            "The node output text does not carry the results; read them from the list parameter.",
        ),
        examples=(
            ActionExample(
                title="Collect file metadata into a report list",
                node={
                    "id": "FILE_INFO",
                    "action_type": "functions",
                    "action_parameters": {
                        "functions": {
                            "size": {
                                "function_name": "file_size",
                                "function_parameters": {"file_path": "param.current_file"},
                            },
                            "md5": {
                                "function_name": "md5_check_sum_file",
                                "function_parameters": {"file_path": "param.current_file"},
                            },
                        },
                        "save_to_list": "file_report",
                    },
                    "transitions": [{"next": "NEXT_NODE"}],
                },
            ),
        ),
    ),
)
class FunctionsAction(BaseAutomaticAction):
    """Executes multiple registered functions and saves their outputs as a dictionary.

    Each function output text is stored under its configured key, and the dictionary is appended to a list.
    """
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


@register_action(
    "Stops the workflow execution.",
    metadata=ActionOperatorMetadata(
        description=(
            "Ends the workflow at this node. Without a function the node passes the previous "
            "output text through. With 'function_name' the registered function runs first and its "
            "result becomes the final output of the workflow."
        ),
        optional_parameters={
            "function_name": ActionParameterDoc(
                "str", "Registered function to execute before stopping; its result is the final output."
            ),
            "function_parameters": _FUNCTION_PARAMETERS_DOC,
            "save_as": _SAVE_AS_DOC,
        },
        node_template={
            "id": "<node-id>",
            "action_type": "stop",
            "action_parameters": {},
        },
        transition_hints=(
            "A stop node usually declares no routing transitions; the workflow ends after it.",
        ),
        examples=(
            ActionExample(
                title="End the workflow after the last step",
                node={"id": "END", "action_type": "stop", "action_parameters": {}},
            ),
        ),
    ),
)
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


@register_action(
    "Stops the workflow execution on error.",
    metadata=ActionOperatorMetadata(
        description=(
            "Ends the workflow when a specific error code is present. With 'function_name' the "
            "registered function runs and its output is checked for the code; without a function "
            "the previous output is checked. The configured 'error_code' selects which error stops "
            "the workflow."
        ),
        required_parameters={
            "error_code": ActionParameterDoc("str", "Error code that stops the workflow when present in the output.")
        },
        optional_parameters={
            "function_name": ActionParameterDoc(
                "str", "Registered function whose output is checked instead of the previous output."
            ),
            "function_parameters": _FUNCTION_PARAMETERS_DOC,
            "save_as": _SAVE_AS_DOC,
        },
        node_template={
            "id": "<node-id>",
            "action_type": "stop_on_error",
            "action_parameters": {"error_code": "<error-code>"},
        },
        transition_hints=(
            "Route this node from an 'errors' transition of the failing node to end the run cleanly.",
        ),
        examples=(
            ActionExample(
                title="Stop the workflow when a copy failed",
                node={
                    "id": "STOP_ON_COPY_FAIL",
                    "action_type": "stop_on_error",
                    "action_parameters": {"error_code": "copy_failed"},
                },
            ),
        ),
    ),
)
class StopOnError(StopAction):
    """Stops the workflow execution on specific error_code from output.
    - If function is provided - check error code in function output.
    - if function is not provided - check error code in previous output"""
    ACTION_TYPE: ClassVar[str] = "stop_on_error"
    error_code: Annotated[str, "Error code to stop the workflow on"]

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.error_code = parameter_from_dict(data, "error_code", str)
