from collections import deque
from pathlib import Path

from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.function_registry import register_function
from workflow_engine.validators.functions_validators import folder_exists_arg_validator, not_empty_str_arg_validator


def set_items(
        param_writes: dict[str,ParamWrite],
        deque_name:str,
        items:list[object],
        set_mode:bool,
        cur_param_name_suffix: str | None = None,
        set_cur_param: bool = False,
        on_empty_items: str | None = None,

) -> None:
    if cur_param_name_suffix is not None and set_cur_param:
        cur_param = f"cur_{cur_param_name_suffix}"
        if len(items) > 0:
            param_writes[cur_param] = ParamWrite(mode=WriteParamMode.SET, value=items.pop(0), allow_overwrite=True)
        elif on_empty_items is not None:
            param_writes[cur_param] = ParamWrite(mode=WriteParamMode.SET, value=on_empty_items, allow_overwrite=True)

    if set_mode:
        param_writes[deque_name] = ParamWrite(mode=WriteParamMode.SET, value=deque(items))
    elif len(items) > 0:
        param_writes[deque_name] = ParamWrite(mode=WriteParamMode.EXTEND, value=items)



@register_function(
    decorators=[
        folder_exists_arg_validator({"path_target": 0}),
        not_empty_str_arg_validator({"folder_deque_name": 1, "file_deque_name": 2})
    ]
)
def read_folder_items_to_deque(
        path_target: str,
        folder_deque_name: str,
        file_deque_name: str,
        state: StateReadOnlyView,
        on_empty_items: str | None = "empty"
) -> ActionNodeOutput:
    """
    Read directory items and prepare state updates for file and folder.
    Set cur_file and cur_folder parameters - first item from list with allow_overwrite=True if lists is not empty.
    Set folder deque and file deque with the remaining items.

    Args:
        path_target: Path to the target directory to scan.
        folder_deque_name: Name of the state parameter that stores folder paths in a deque.
        file_deque_name: Name of the state parameter that stores file paths in a deque.
        state: Read-only state view used to check whether deque parameters already exist.
        on_empty_items: Value to return if the deque is empty.

    Returns:
        ActionNodeOutput containing:
        - output_text: Absolute POSIX path of the scanned directory.
        - param_writes: Updates for file/folder deques and current file/folder parameters.
    """
    folder = Path(path_target)
    list_of_paths = [item.absolute() for item in folder.iterdir() if item.is_dir() or item.is_file()]
    param_writes:dict[str,ParamWrite] = {}
    list_of_files = [item for item in list_of_paths if item.is_file()]
    set_items(
        param_writes, file_deque_name, list_of_files,
        set_mode=state.get_param(file_deque_name) is None,
        cur_param_name_suffix="file",
        set_cur_param=True,
        on_empty_items=on_empty_items,

    )
    list_of_folders = [item for item in list_of_paths if item.is_dir()]
    set_items(
        param_writes, folder_deque_name, list_of_folders,
        set_mode=state.get_param(folder_deque_name) is None,
        cur_param_name_suffix="folder",
        set_cur_param=True,
        on_empty_items=on_empty_items,

    )
    return ActionNodeOutput(
        output_text=folder.absolute().as_posix(),
        param_writes = param_writes
    )

@register_function()
def set_param_from_deque(
        deque_param_name: str,
        param_name: str,
        state: StateReadOnlyView,
        on_empty:str = "empty",
        on_set:str = "popleft_from_deque",
        error_not_found: str = "deque_not_found",
) -> ActionNodeOutput:
    """
    Set a parameter from the front of a deque parameter.

        :param on_set: Value to return when a parameter is successfully set from the deque.
        :param deque_param_name: Name of the deque parameter to pop from.
        :param param_name: Name of the parameter to set with the popped value.
        :param on_empty: Value to return if the deque is empty.
        :param state: Read-only state view used to access the deque parameter.
        :param error_not_found: Error code to return if the deque parameter is not found.

    :returns: ActionNodeOutput containing:
        - output_text: Value popped from the deque.
        - param_writes: Updates for the parameter set from the deque.
        - error_not_found: Error code to return if the deque parameter is not found.
    """
    deque_obj = state.get_param(deque_param_name, deque)
    if isinstance(deque_obj, deque):
        if len(deque_obj) == 0:
            return ActionNodeOutput(
                output_text=on_empty,
                param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=on_empty, allow_overwrite=True)}
            )
        else:
            value = deque_obj.popleft()
            param_writes = {
                deque_param_name: ParamWrite(mode=WriteParamMode.POP_LEFT, value=None),
                param_name: ParamWrite(mode=WriteParamMode.SET, value=value, allow_overwrite=True)
            }
            return ActionNodeOutput(
                output_text=on_set,
                param_writes=param_writes
            )
    return ActionNodeOutput(
        output_text="",
        error_code=error_not_found,
        error_msg=f"Deque parameter '{deque_param_name}' not found in state.",
    )