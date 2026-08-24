import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from prettytable import PrettyTable

from workflow_engine.exceptions import ActionConfigurationError
from workflow_engine.models.state import (
    ARTIFACT_NOT_FOUND,
    ARTIFACT_OVERWRITE,
    ARTIFACT_PATH_CONFLICT,
    StateReadOnlyView,
)
from workflow_engine.output import ActionNodeOutput, WorkflowArtifact
from workflow_engine.registry.function_registry import register_function
from workflow_engine.text_interpolation import is_template_text, resolve_template_text, validate_template_text
from workflow_engine.tools import render_value_as_text
from workflow_engine.validators.functions_validators import not_empty_str_arg_validator

COPY_ARTIFACT_WRITE_ERROR = "copy_artifact_write_error"
GROUPED_TABLES_NO_DATA = "grouped_tables_no_data"
GROUPED_TABLES_KEY_MISSING = "grouped_tables_key_missing"
GROUPED_TABLES_WRITE_ERROR = "grouped_tables_write_error"
TEXT_ARTIFACT_NOT_TEXT = "text_artifact_not_text"
TEXT_ARTIFACT_WRITE_ERROR = "text_artifact_write_error"
TEMPLATE_PATH_UNRESOLVED = "template_path_unresolved"
TEMPLATE_NOT_FOUND = "template_not_found"
TEMPLATE_READ_ERROR = "template_read_error"
TEMPLATE_MALFORMED = "template_malformed"
TEMPLATE_WRITE_ERROR = "template_write_error"


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
    summary="Convert a list of dictionaries to a pretty table artifact",
)
def dict_list_to_pretty_table(
    artifact_name: Annotated[str, "Name of the artifact to create"],
    dict_param_name: Annotated[str, "Name of the parameter containing the list of dictionaries"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to access parameters and artifacts"],
    artifact_path: Annotated[str | Path | None, "Path to the artifact"] = None,
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
        with absolute_path.open("w", encoding="utf-8", newline="") as file:
            file.write(pretty_table_str(table_format, table))
    except OSError as e:
        return ActionNodeOutput(output_text="", error_code="pretty_table_write_error", error_msg=str(e))

    return ActionNodeOutput(
        output_text="pretty_table_created",
        artifacts={
            artifact_name: WorkflowArtifact(artifact_path, datetime.now(tz=UTC), description=artifact_description)
        },
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"source_artifact_name": 0, "target_artifact_name": 1})],
    summary="Copy a registered artifact into a new registered artifact",
)
def copy_artifact(
    source_artifact_name: Annotated[str, "Logical name of an existing artifact to copy from"],
    target_artifact_name: Annotated[str, "Logical name the copy is registered under"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to resolve and register artifacts"],
    target_path: Annotated[
        str | None,
        "Path of the copy inside work_dir/artifacts; defaults to the target name with the source file suffix",
    ] = None,
    allow_overwrite: Annotated[
        bool, "When False (default) an existing target name or path is refused; when True the copy proceeds"
    ] = False,
) -> ActionNodeOutput:
    """Copy an existing artifact to a new artifact and register the copy.

    This is the copy-promote vehicle: a draft artifact produced on a working node is copied to the
    name declared as a deliverable. The copy is resolved inside work_dir/artifacts and a path
    outside it is rejected. When target_path is omitted the copy lands in the artifacts root under
    the target name with the source file suffix. The function copies only; the source artifact stays
    registered and on disk.
    On an unknown source name returns error_code 'artifact_not_found'.
    When allow_overwrite is False and the target name already exists returns error_code
    'artifact_overwritten', and a target path already backing another artifact returns
    'artifact_path_conflict'.
    On an OS error while copying returns error_code 'copy_artifact_write_error'.
    """
    if not state.is_artifact_exist_by_name(source_artifact_name):
        return ActionNodeOutput(
            output_text="",
            error_code=ARTIFACT_NOT_FOUND,
            error_msg=f"Source artifact '{source_artifact_name}' is not registered.",
        )

    source_relative = state.get_artifacts()[source_artifact_name]
    source_absolute = state.get_artifact_absolute_path(source_relative)

    default_name = target_artifact_name + Path(source_relative).suffix
    target_relative = state.get_artifact_relative_path(target_path if target_path else default_name)

    if not allow_overwrite:
        conflict = check_artifact(target_artifact_name, target_relative, state)
        if conflict is not None:
            return conflict

    target_absolute = state.get_artifact_absolute_path(target_relative)
    try:
        target_absolute.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_absolute, target_absolute)
    except OSError as e:
        return ActionNodeOutput(output_text="", error_code=COPY_ARTIFACT_WRITE_ERROR, error_msg=str(e))

    return ActionNodeOutput(
        output_text="artifact_copied",
        artifacts={
            target_artifact_name: WorkflowArtifact(
                target_relative,
                datetime.now(tz=UTC),
                description=f"Copy of artifact '{source_artifact_name}'",
            )
        },
    )


def _write_artifact_text(
    artifact_name: str,
    artifact_path: str | Path | None,
    artifact_description: str,
    default_name: str,
    content: str,
    state: StateReadOnlyView,
    write_error_code: str,
    output_text: str,
) -> ActionNodeOutput:
    """Write composed text under work_dir/artifacts and register it. See ADR 020 §1.

    The three output functions differ in how they compose their text and share everything after it:
    the artifact path resolution, the refusal of an existing name or path, and the registration.
    """
    relative_path = state.get_artifact_relative_path(artifact_path if artifact_path else default_name)
    conflict = check_artifact(artifact_name, relative_path, state)
    if conflict is not None:
        return conflict

    absolute_path = state.get_artifact_absolute_path(relative_path)
    try:
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        with absolute_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(content)
    except OSError as e:
        return ActionNodeOutput(output_text="", error_code=write_error_code, error_msg=str(e))

    return ActionNodeOutput(
        output_text=output_text,
        artifacts={
            artifact_name: WorkflowArtifact(relative_path, datetime.now(tz=UTC), description=artifact_description)
        },
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"artifact_name": 0, "dict_param_name": 1, "group_by": 2})],
    summary="Write a list of dictionaries as one table per group, each under its heading",
)
def dict_list_to_grouped_tables(
    artifact_name: Annotated[str, "Name of the artifact to create"],
    dict_param_name: Annotated[str, "Name of the parameter containing the list of dictionaries"],
    group_by: Annotated[str, "Key whose value groups the rows and heads each section"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to access parameters and artifacts"],
    artifact_path: Annotated[str | Path | None, "Path to the artifact"] = None,
    artifact_description: Annotated[str | None, "Description of the artifact"] = None,
    table_format: Annotated[str | None, "Format of the tables inside the document"] = None,
) -> ActionNodeOutput:
    """Write one composed document holding a table per group instead of one table over everything.

    Each section is the group value as a heading line, an empty line, and the rows of that group as
    a table; sections are separated by an empty line and ordered by their heading. The grouping key
    heads its section and is therefore dropped from the rows. Available table formats: 'html',
    'csv', 'json', 'latex', 'mediawiki'. Default is plain text. The composed file is a document for
    a reader: with a markup format each section is valid, the file around them is not.
    If the parameter does not hold a non-empty list of dictionaries, returns error_code
    'grouped_tables_no_data'.
    If a row does not carry the grouping key, returns error_code 'grouped_tables_key_missing'.
    If the artifact already exists in the state, returns error_code 'artifact_overwritten', and a
    path already backing another artifact returns 'artifact_path_conflict'.
    On an OS error while writing returns error_code 'grouped_tables_write_error'.
    """
    dict_list = state.get_param(dict_param_name, list)
    if not isinstance(dict_list, list) or not dict_list:
        return ActionNodeOutput(output_text="", error_code=GROUPED_TABLES_NO_DATA)

    groups: dict[str, list[dict[str, object]]] = {}
    for row in dict_list:
        if not isinstance(row, dict) or group_by not in row:
            return ActionNodeOutput(
                output_text="",
                error_code=GROUPED_TABLES_KEY_MISSING,
                error_msg=f"Every row must carry the grouping key '{group_by}'.",
            )
        heading = render_value_as_text(row[group_by])
        groups.setdefault(heading, []).append({key: value for key, value in row.items() if key != group_by})

    sections = []
    for heading in sorted(groups):
        rows = groups[heading]
        table = PrettyTable()
        table.field_names = list(rows[0].keys())
        for row in rows:
            table.add_row([row.get(field_name) for field_name in table.field_names])
        sections.append(f"{heading}\n\n{pretty_table_str(table_format, table)}")

    return _write_artifact_text(
        artifact_name=artifact_name,
        artifact_path=artifact_path,
        artifact_description=artifact_description
        if artifact_description
        else f"Tables grouped by '{group_by}' from parameter: {dict_param_name}",
        default_name=artifact_name + ".txt",
        content="\n\n".join(sections) + "\n",
        state=state,
        write_error_code=GROUPED_TABLES_WRITE_ERROR,
        output_text="grouped_tables_created",
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"artifact_name": 0})],
    summary="Write a text value as an artifact, exactly as it stands",
)
def write_text_artifact(
    artifact_name: Annotated[str, "Name of the artifact to create"],
    text: Annotated[str, "The text to write; a 'param.'/'output.' reference resolves to its value"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to access parameters and artifacts"],
    artifact_path: Annotated[str | Path | None, "Path to the artifact"] = None,
    artifact_description: Annotated[str | None, "Description of the artifact"] = None,
) -> ActionNodeOutput:
    """Write a text value as an artifact without composing anything.

    This is the base text write: whatever a node produced as text — the reply of a model above all —
    becomes a file and a registered artifact in the format it was authored in. The engine writes
    bytes and reads no meaning into them.
    A value that is not a string returns error_code 'text_artifact_not_text': a collection is not
    silently serialized here.
    If the artifact already exists in the state, returns error_code 'artifact_overwritten', and a
    path already backing another artifact returns 'artifact_path_conflict'.
    On an OS error while writing returns error_code 'text_artifact_write_error'.
    """
    if not isinstance(text, str):
        return ActionNodeOutput(
            output_text="",
            error_code=TEXT_ARTIFACT_NOT_TEXT,
            error_msg=f"'text' must be a string, got {type(text).__name__}.",
        )

    return _write_artifact_text(
        artifact_name=artifact_name,
        artifact_path=artifact_path,
        artifact_description=artifact_description if artifact_description else f"Text artifact '{artifact_name}'",
        default_name=artifact_name + ".txt",
        content=text,
        state=state,
        write_error_code=TEXT_ARTIFACT_WRITE_ERROR,
        output_text="text_artifact_created",
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"artifact_name": 0, "template_path": 1})],
    summary="Render an authored template file into an artifact",
)
def render_template_to_artifact(
    artifact_name: Annotated[str, "Name of the artifact to create"],
    template_path: Annotated[str, "Path of the template file: absolute, or relative to the workflow definition"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to access parameters and artifacts"],
    artifact_path: Annotated[str | Path | None, "Path to the artifact"] = None,
    artifact_description: Annotated[str | None, "Description of the artifact"] = None,
) -> ActionNodeOutput:
    """Render an authored template file against the state and write the result as an artifact.

    The file is template text in the sense of ADR 016: '${param.<name>}', '${output.<node_id>}' and
    '${artifact.<logical_name>}' are replaced by their values, '$$' writes a literal '$', and
    nothing else is interpreted — a template substitutes values, it never iterates. A file carrying
    no '$' is written as it stands. The path is used as written when absolute and resolved against
    the directory of the workflow definition file when relative.
    When a relative path cannot be resolved because the session does not record the definition
    directory, returns error_code 'template_path_unresolved'.
    A missing file returns error_code 'template_not_found' and an unreadable one
    'template_read_error'.
    A malformed placeholder returns error_code 'template_malformed'; a reference that does not
    resolve fails the run at this node, as an unresolved reference does anywhere else.
    If the artifact already exists in the state, returns error_code 'artifact_overwritten', and a
    path already backing another artifact returns 'artifact_path_conflict'.
    On an OS error while writing returns error_code 'template_write_error'.
    """
    resolved_template = state.resolve_authored_path(template_path)
    if resolved_template is None:
        return ActionNodeOutput(
            output_text="",
            error_code=TEMPLATE_PATH_UNRESOLVED,
            error_msg=(
                f"Relative template path '{template_path}' cannot be resolved: this session does not "
                "record the directory of its workflow definition. Use an absolute path."
            ),
        )
    if not resolved_template.is_file():
        return ActionNodeOutput(
            output_text="",
            error_code=TEMPLATE_NOT_FOUND,
            error_msg=f"Template file not found: {resolved_template.as_posix()}",
        )
    try:
        content = resolved_template.read_text(encoding="utf-8-sig")
    except OSError as e:
        return ActionNodeOutput(output_text="", error_code=TEMPLATE_READ_ERROR, error_msg=str(e))

    if is_template_text(content):
        try:
            validate_template_text("render_template_to_artifact", resolved_template.name, content)
        except ActionConfigurationError as e:
            return ActionNodeOutput(output_text="", error_code=TEMPLATE_MALFORMED, error_msg=str(e))
        content = resolve_template_text(state, content)

    return _write_artifact_text(
        artifact_name=artifact_name,
        artifact_path=artifact_path,
        artifact_description=artifact_description
        if artifact_description
        else f"Rendered from template '{resolved_template.name}'",
        default_name=artifact_name + resolved_template.suffix,
        content=content,
        state=state,
        write_error_code=TEMPLATE_WRITE_ERROR,
        output_text="template_rendered",
    )
