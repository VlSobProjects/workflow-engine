import shutil
from pathlib import Path
from typing import Annotated

from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    register_function,
)
from workflow_engine.validators.functions_validators import (
    file_exists_arg_validator,
    folder_exists_arg_validator,
    not_empty_str_arg_validator,
)


@register_function(
    decorators=[
        file_exists_arg_validator({"path_source": 0}),
    ],
    summary="Copy a file",
)
def copy_file(
        path_source: Annotated[str, "Path to the source file"],
        path_target: Annotated[str, "Path to the target file"]
) -> ActionNodeOutput:
    """Copy a file from source to target."""
    source = Path(path_source)
    if not source.is_file():
        return ActionNodeOutput(
            output_text="Can't copy file",
            error_code="file_not_found",
            error_msg=f"Source file '{source.absolute()}' is not a file or does not exist.",
        )
    target = Path(path_target)
    if not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
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
        path_target: Annotated[str, "Path to the target folder"],
        folder_name: Annotated[str, "Name of the folder to create"]
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


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="Delete a file"
)
def file_delete(file_path: Annotated[str, "Path to the file to delete"]) -> ActionNodeOutput:
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
