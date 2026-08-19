import shutil
from pathlib import Path
from typing import Annotated

from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    register_function,
)
from workflow_engine.tools import render_value_as_text
from workflow_engine.validators.functions_validators import (
    file_exists_arg_validator,
    folder_exists_arg_validator,
    not_empty_str_arg_validator,
)


@register_function(summary="Emit a value as the action output.")
def echo_value(
    value: Annotated[
        str, "Value to emit; supports 'param.<name>', 'output.<node_id>' and 'artifact.<logical_name>' references"
    ],
) -> ActionNodeOutput:
    """Emit the given value unchanged as the output text of the action.

    The main operator use is to surface a state parameter into a node output so transition guards
    can evaluate it, because guards read the action result and never the state. A non-string value
    is emitted as its string representation.
    """
    return ActionNodeOutput(output_text=render_value_as_text(value))


@register_function(
    decorators=[
        file_exists_arg_validator({"path_source": 0}),
    ],
    summary="Copy a file to a target file path",
)
def copy_file(
    path_source: Annotated[str | Path, "Path to the source file"],
    path_target: Annotated[str | Path, "Full path of the copy, including its file name"],
) -> ActionNodeOutput:
    """Copy a file to the given target path, which is always the full path of the copy.

    The target is never interpreted as a folder: to copy into a folder under the source file name,
    use 'copy_file_to_folder'. The folder holding the target is not created; it must already exist.
    If the target path is an existing folder, returns an ActionNodeOutput with error_code
    'target_is_folder' and the error message.
    If the folder holding the target does not exist, returns an ActionNodeOutput with error_code
    'target_folder_not_found' and the error message.
    On OsError during copying, returns an ActionNodeOutput with error_code 'copy_failed' and the
    error message.
    """
    source = Path(path_source)
    target = Path(path_target)
    if target.is_dir():
        return ActionNodeOutput(
            output_text="Can't copy file",
            error_code="target_is_folder",
            error_msg=f"Target '{target.absolute().as_posix()}' is an existing folder; "
            f"use 'copy_file_to_folder' to copy into a folder under the source file name.",
        )
    if not target.parent.is_dir():
        return ActionNodeOutput(
            output_text="Can't copy file",
            error_code="target_folder_not_found",
            error_msg=f"Target folder '{target.parent.absolute().as_posix()}' does not exist.",
        )
    return _copy(source, target)


@register_function(
    decorators=[
        file_exists_arg_validator({"path_source": 0}),
    ],
    summary="Copy a file into an existing folder",
)
def copy_file_to_folder(
    path_source: Annotated[str | Path, "Path to the source file"],
    path_target_folder: Annotated[str | Path, "Path to an existing folder to copy the file into"],
) -> ActionNodeOutput:
    """Copy a file into an existing folder, keeping the source file name.

    The folder is not created; it must already exist. To copy under a different name, use
    'copy_file' with the full path of the copy.
    If the target folder does not exist, returns an ActionNodeOutput with error_code
    'target_folder_not_found' and the error message.
    On OsError during copying, returns an ActionNodeOutput with error_code 'copy_failed' and the
    error message.
    """
    source = Path(path_source)
    target_folder = Path(path_target_folder)
    if not target_folder.is_dir():
        return ActionNodeOutput(
            output_text="Can't copy file",
            error_code="target_folder_not_found",
            error_msg=f"Target folder '{target_folder.absolute().as_posix()}' does not exist.",
        )
    return _copy(source, target_folder / source.name)


def _copy(source: Path, target: Path) -> ActionNodeOutput:
    """Copy the source file to the resolved target path and report the failure as an error code."""
    try:
        shutil.copyfile(source, target)
    except OSError as e:
        return ActionNodeOutput(
            output_text="Can't copy file",
            error_code="copy_failed",
            error_msg=f"Failed to copy file from '{source.absolute().as_posix()}' "
            f"to '{target.absolute().as_posix()}': {e!s}",
        )
    return ActionNodeOutput(output_text=target.absolute().as_posix())


@register_function(
    decorators=[folder_exists_arg_validator({"path_target": 0}), not_empty_str_arg_validator({"folder_name": 1})],
    summary="Create a folder",
)
def create_folder(
    path_target: Annotated[str | Path, "Path to the target folder"],
    folder_name: Annotated[str, "Name of the folder to create"],
) -> ActionNodeOutput:
    """Create a folder at the specified target path with the given folder name."""
    folder = Path(path_target) / folder_name
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return ActionNodeOutput(
            output_text="Can't create folder",
            error_code="create_failed",
            error_msg=f"Failed to create folder '{folder.absolute().as_posix()}': {e!s}",
        )
    return ActionNodeOutput(output_text=folder.absolute().as_posix())


@register_function(decorators=[file_exists_arg_validator({"file_path": 0})], summary="Delete a file")
def file_delete(file_path: Annotated[str | Path, "Path to the file to delete"]) -> ActionNodeOutput:
    """Delete a file at the specified path."""
    file = Path(file_path)
    try:
        file.unlink()
    except OSError as e:
        return ActionNodeOutput(
            output_text="Can't delete file",
            error_code="delete_failed",
            error_msg=f"Failed to delete file '{file.absolute().as_posix()}': {e!s}",
        )
    return ActionNodeOutput(output_text=f"File '{file.absolute().as_posix()}' deleted successfully")
