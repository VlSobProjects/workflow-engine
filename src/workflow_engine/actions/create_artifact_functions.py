from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from prettytable import PrettyTable

from workflow_engine.models.state import ARTIFACT_OVERWRITE, ARTIFACT_PATH_CONFLICT, StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, WorkflowArtifact
from workflow_engine.registry.function_registry import register_function
from workflow_engine.validators.functions_validators import not_empty_str_arg_validator


def check_artifact(artifact_name: str, relative_path: Path, state: StateReadOnlyView) -> ActionNodeOutput | None:
    if state.is_artifact_exist_by_name(artifact_name):
        return ActionNodeOutput(
            output_text="",
            error_code=ARTIFACT_OVERWRITE,
            error_msg=f"Artifact '{artifact_name}'already exists in state. Overwriting is not allowed. "
            f"Artifact with path: {relative_path} will not be created",
        )
    if state.is_artifact_exist_by_path(relative_path):
        return ActionNodeOutput(
            output_text="",
            error_code=ARTIFACT_PATH_CONFLICT,
            error_msg=f"Artifact name: '{artifact_name}' at path '{relative_path}' "
            "already exists in state. Overwriting is not allowed.",
        )
    return None


def pretty_table_str(table_format: str | None, table: PrettyTable) -> str:
    match table_format:
        case "html":
            return table.get_html_string()
        case "csv":
            return table.get_csv_string()
        case "json":
            return table.get_json_string()
        case "latex":
            return table.get_latex_string()
        case "mediawiki":
            return table.get_mediawiki_string()
        case _:
            return table.get_string()


@register_function(
    decorators=[not_empty_str_arg_validator({"artifact_name": 0, "dict_param_name": 1})],
    summary="Convert a list of dictionaries to a pretty table artifact"
)
def dict_list_to_pretty_table(
    artifact_name: Annotated[str, "Name of the artifact to create"],
    dict_param_name: Annotated[str, "Name of the parameter containing the list of dictionaries"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to access parameters and artifacts"],
    artifact_path: Annotated[str | None, "Path to the artifact"] = None,
    artifact_description: Annotated[str | None, "Description of the artifact"] = None,
    table_format: Annotated[str | None, "Format of the pretty table"] = None,
) -> ActionNodeOutput:
    """Convert a list of dictionaries to a pretty table and save it as an artifact.
    Available table formats: 'html', 'csv', 'json', 'latex', 'mediawiki'. Default is plain text.
    On OsError during file writing, returns an ActionNodeOutput with error_code
    'pretty_table_write_error' and the error message.
    If the artifact already exists in the state, returns an ActionNodeOutput with error_code
    'pretty_table_artifact_exists' and the error message.
    If the parameter does not contain a list of dictionaries, or contains an empty list, returns an
    ActionNodeOutput with error_code 'pretty_table_no_data'.
    """
    dict_list = state.get_param(dict_param_name, list)
    if not isinstance(dict_list, list) or not dict_list:
        return ActionNodeOutput(output_text="", error_code="pretty_table_no_data")

    artifact_path = state.get_artifact_relative_path(artifact_path if artifact_path else artifact_name + ".txt")
    artifact_description = (
        artifact_description if artifact_description else f"Pretty table text from parameter: {dict_param_name}"
    )
    resp = check_artifact(artifact_name, artifact_path, state)

    if resp is not None:
        return resp

    absolute_path = state.get_artifact_absolute_path(artifact_path)

    table = PrettyTable()
    table.field_names = list(dict_list[0].keys())
    for item in dict_list:
        table.add_row(list(item.values()))
    try:
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        with absolute_path.open("w") as file:
            file.write(pretty_table_str(table_format, table))
    except OSError as e:
        return ActionNodeOutput(output_text="", error_code="pretty_table_write_error", error_msg=str(e))

    return ActionNodeOutput(
        output_text="pretty_table_created",
        artifacts={
            artifact_name: WorkflowArtifact(artifact_path, datetime.now(tz=UTC), description=artifact_description)
        },
    )
