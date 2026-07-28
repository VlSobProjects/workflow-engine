import shutil
from pathlib import Path

from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import register_function
from workflow_engine.validators.functions_validators import (
    action_file_exists_arg_validator,
)


@register_function(decorators=(
    action_file_exists_arg_validator({"path_source": 0}),
))
def copy_file(path_source:str,path_target:str)->ActionNodeOutput:
    source = Path(path_source)
    if not source.is_file():
        return ActionNodeOutput(
            output="Can't copy file",
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
            output="Can't copy file",
            error_code="copy_failed",
            error_message=f"Failed to copy file from '{source.absolute()}' to '{target.absolute()}': {e!s}"
        )
    return ActionNodeOutput(
        output=str(target)
    )




