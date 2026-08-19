from collections import deque
from pathlib import Path
from typing import Annotated

from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.function_registry import register_function
from workflow_engine.validators.functions_validators import folder_exists_arg_validator, not_empty_str_arg_validator


def set_items(
    param_writes: dict[str, ParamWrite],
    deque_name: str,
    items: list[object],
    set_mode: bool,
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
        not_empty_str_arg_validator({"folder_deque_name": 1, "file_deque_name": 2}),
    ],
    summary="Reads the paths in a folder into two deques",
)
def read_folder_items_to_deque(
    path_target: Annotated[str | Path, "Path to the target directory to scan"],
    folder_deque_name: Annotated[str, "Name of the state parameter that stores folder paths in a deque"],
    file_deque_name: Annotated[str, "Name of the state parameter that stores file paths in a deque"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to check whether deque parameters already exist"],
    on_empty_items: Annotated[str | None, "Value to return if the deque is empty default 'empty'"] = "empty",
) -> ActionNodeOutput:
    """Read directory paths and prepare state updates for files and folders.
    Set cur_file and cur_folder parameters - first item from list with allow_overwrite=True if lists is not empty.
    Set folder deque and file deque with the remaining items.
    """
    folder = Path(path_target)
    list_of_paths = [item.absolute() for item in folder.iterdir() if item.is_dir() or item.is_file()]
    param_writes: dict[str, ParamWrite] = {}
    list_of_files = [item for item in list_of_paths if item.is_file()]
    set_items(
        param_writes,
        file_deque_name,
        list_of_files,
        set_mode=state.get_param(file_deque_name) is None,
        cur_param_name_suffix="file",
        set_cur_param=True,
        on_empty_items=on_empty_items,
    )
    list_of_folders = [item for item in list_of_paths if item.is_dir()]
    set_items(
        param_writes,
        folder_deque_name,
        list_of_folders,
        set_mode=state.get_param(folder_deque_name) is None,
        cur_param_name_suffix="folder",
        set_cur_param=True,
        on_empty_items=on_empty_items,
    )
    return ActionNodeOutput(output_text=folder.absolute().as_posix(), param_writes=param_writes)


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 0})],
    summary="Initializes a deque parameter from a list of items.",
)
def init_deque_param(
    param_name: Annotated[str, "Name of the state parameter to create as a deque"],
    items: Annotated[list | None, "Initial items of the deque, front first; empty when omitted"] = None,
) -> ActionNodeOutput:
    """Create a deque parameter seeded with the given items.

    The main operator use is to prepare a work queue before a traversal loop: seed it with the
    starting items, extend it with functions such as 'enqueue_folder_entries', and consume it
    with 'set_param_from_deque'.
    """
    return ActionNodeOutput(
        output_text=param_name,
        param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=deque(items or []))},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 0})],
    summary="Initializes an empty list parameter.",
)
def init_list_param(
    param_name: Annotated[str, "Name of the state parameter to create as an empty list"],
) -> ActionNodeOutput:
    """Create an empty list parameter.

    The main operator use is to prepare an accumulator before a loop that appends to it, for
    example the 'functions' action with 'save_to_list' or 'dict_list_to_pretty_table'.
    """
    return ActionNodeOutput(
        output_text=param_name,
        param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=[])},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"deque_param_name": 1})],
    summary="Extends a deque parameter with the entries of a folder.",
)
def enqueue_folder_entries(
    folder_path: Annotated[str | Path, "Path to the folder whose files and subfolders are enqueued"],
    deque_param_name: Annotated[str, "Name of the existing deque parameter to extend"],
) -> ActionNodeOutput:
    """Extend an existing deque parameter with the sorted entries of a folder.

    Files and subfolders are enqueued together as resolved POSIX paths, so repeated application
    combined with 'set_param_from_deque' walks a tree breadth-first. Returns the error code
    'folder_not_found' when the path is not a directory.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return ActionNodeOutput(
            output_text="",
            error_code="folder_not_found",
            error_msg=f"Folder '{folder_path}' does not exist",
        )

    entries = sorted(item.resolve().as_posix() for item in folder.iterdir() if item.is_dir() or item.is_file())
    if len(entries) > 0:
        return ActionNodeOutput(
            output_text=folder.resolve().as_posix(),
            param_writes={deque_param_name: ParamWrite(mode=WriteParamMode.EXTEND, value=entries)},
        )
    return ActionNodeOutput(output_text=folder.resolve().as_posix())


@register_function(summary="Pops an item from the front of a deque.")
def set_param_from_deque(
    deque_param_name: Annotated[str, "Name of the deque parameter to pop from"],
    param_name: Annotated[str, "Name of the parameter to set with the popped value"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to access the deque parameter"],
    on_empty: Annotated[str, "Value to return if the deque is empty default 'empty'"] = "empty",
    on_set: Annotated[
        str, "Value to return when a parameter is successfully set from the deque default 'popleft_from_deque'"
    ] = "popleft_from_deque",
    error_not_found: Annotated[
        str, "Error code to return if the deque parameter is not found default 'deque_not_found'"
    ] = "deque_not_found",
) -> ActionNodeOutput:
    """Pops an item from the front of a deque parameter and sets it to another parameter.
    If the deque is empty, sets the target parameter to a specified value.
    Returns an error if the deque parameter is not found."""
    deque_obj = state.get_param(deque_param_name, deque)
    if isinstance(deque_obj, deque):
        if len(deque_obj) == 0:
            return ActionNodeOutput(
                output_text=on_empty,
                param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=on_empty, allow_overwrite=True)},
            )
        else:
            value = deque_obj.popleft()
            param_writes = {
                deque_param_name: ParamWrite(mode=WriteParamMode.POP_LEFT, value=None),
                param_name: ParamWrite(mode=WriteParamMode.SET, value=value, allow_overwrite=True),
            }
            return ActionNodeOutput(output_text=on_set, param_writes=param_writes)
    return ActionNodeOutput(
        output_text="",
        error_code=error_not_found,
        error_msg=f"Deque parameter '{deque_param_name}' not found in state.",
    )
