import hashlib
import shutil
from pathlib import Path

from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    register_function,
)
from workflow_engine.validators.functions_validators import (
    file_exists_arg_validator,
    folder_exists_arg_validator,
    not_empty_str_arg_validator,
)


@register_function(decorators=[
        file_exists_arg_validator({"path_source": 0}),
])
def copy_file(path_source:str,path_target:str)->ActionNodeOutput:
    source = Path(path_source)
    if not source.is_file():
        return ActionNodeOutput(
            output_text="Can't copy file",
            error_code="file_not_found",
            error_message=f"Source file '{source.absolute()}' is not a file or does not exist."
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
            error_message=f"Failed to copy file from '{source.absolute()}' to '{target.absolute()}': {e!s}"
        )
    return ActionNodeOutput(
        output_text=str(target)
    )


@register_function(
    decorators=[
        folder_exists_arg_validator({"path_target": 0}),
        not_empty_str_arg_validator({"folder_name": 1})
    ]
)
def create_folder(path_target:str, folder_name:str)->ActionNodeOutput:
    folder = Path(path_target) / folder_name
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return ActionNodeOutput(
            output_text="Can't create folder",
            error_code="create_failed",
            error_message=f"Failed to create folder '{folder.absolute()}': {e!s}"
        )
    return ActionNodeOutput(
        output_text=str(folder.absolute())
    )


@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def md5_check_sum_file(file_path: str) -> ActionNodeOutput:
    with open(file_path, 'rb') as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(65536)
            if not data:
                break
            m.update(data)
        return ActionNodeOutput(
            output_text=m.hexdigest()
        )

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_delete(file_path:str)->ActionNodeOutput:
    file = Path(file_path)
    try:
        file.unlink()
    except OSError as e:
        return ActionNodeOutput(
            output_text="Can't delete file",
            error_code="delete_failed",
            error_message=f"Failed to delete file '{file.absolute()}': {e!s}"
        )
    return ActionNodeOutput(
        output_text=f"File '{file.absolute()}' deleted successfully"
    )

@register_function(
    decorators=[
        folder_exists_arg_validator({"folder_path": 0}),
        not_empty_str_arg_validator({"param_name": 1})
    ]
)
def save_list_of_paths(folder_path:str,param_name:str)->ActionNodeOutput:
    folder = Path(folder_path)
    list_of_paths = [item for item in folder.iterdir()]
    return ActionNodeOutput(
        output_text=str(folder.absolute()),
        parameters={param_name: list_of_paths}
    )
