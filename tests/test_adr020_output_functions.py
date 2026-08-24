"""The output composition functions of ADR 020: grouped tables, a text write, a rendered template."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from workflow_engine.actions.create_artifact_functions import (
    dict_list_to_grouped_tables,
    render_template_to_artifact,
    write_text_artifact,
)
from workflow_engine.models.state import ActionParameter, StateModel, StateReadOnlyView
from workflow_engine.output import WorkflowArtifact

ROWS = [
    {"Folder": Path("root/b"), "Name": "second.txt", "Size": "2 KB"},
    {"Folder": Path("root/a"), "Name": "first.txt", "Size": "1 KB"},
    {"Folder": Path("root/a"), "Name": "also-first.txt", "Size": "3 KB"},
]


@pytest.fixture
def build_state(tmp_path):
    def build(params=None, artifacts=None, workflow_dir=None):
        state = StateModel(
            timestamp=datetime.now(tz=UTC),
            work_dir=tmp_path,
            schema_version="1",
            flow_id="test",
            session_id="test-session-id",
            params={
                name: ActionParameter.create(name=name, value=value, source_node_id="test_node_id")
                for name, value in (params or {}).items()
            },
            artifacts=artifacts or {},
            current_node_id="test_node_id",
            workflow_dir=workflow_dir,
        )
        return StateReadOnlyView.from_state(state)

    return build


def artifact_text(tmp_path: Path, relative: str) -> str:
    return (tmp_path / "artifacts" / relative).read_text(encoding="utf-8")


def test_grouped_tables_write_one_section_per_group(build_state, tmp_path):
    state = build_state({"rows": ROWS})

    result = dict_list_to_grouped_tables(
        artifact_name="inventory", dict_param_name="rows", group_by="Folder", state=state
    )

    assert result.error_code is None
    assert result.output_text == "grouped_tables_created"
    text = artifact_text(tmp_path, "inventory.txt")
    assert text.index("root/a") < text.index("root/b")
    assert "first.txt" in text
    assert "second.txt" in text


def test_grouped_tables_drop_the_grouping_key_from_the_rows(build_state, tmp_path):
    state = build_state({"rows": ROWS})

    dict_list_to_grouped_tables(artifact_name="inventory", dict_param_name="rows", group_by="Folder", state=state)

    text = artifact_text(tmp_path, "inventory.txt")
    heading, _, body = text.partition("\n")
    assert heading == "root/a"
    assert "Folder" not in body
    assert "Name" in body
    assert "Size" in body


def test_grouped_tables_keep_the_requested_table_syntax_inside_a_section(build_state, tmp_path):
    state = build_state({"rows": ROWS})

    dict_list_to_grouped_tables(
        artifact_name="inventory", dict_param_name="rows", group_by="Folder", state=state, table_format="csv"
    )

    text = artifact_text(tmp_path, "inventory.txt")
    assert "Name,Size" in text


def test_grouped_tables_report_no_data_for_an_empty_list(build_state, tmp_path):
    state = build_state({"rows": []})

    result = dict_list_to_grouped_tables(
        artifact_name="inventory", dict_param_name="rows", group_by="Folder", state=state
    )

    assert result.error_code == "grouped_tables_no_data"
    assert not (tmp_path / "artifacts").exists()


def test_grouped_tables_refuse_a_row_without_the_grouping_key(build_state, tmp_path):
    state = build_state({"rows": [{"Name": "orphan.txt"}]})

    result = dict_list_to_grouped_tables(
        artifact_name="inventory", dict_param_name="rows", group_by="Folder", state=state
    )

    assert result.error_code == "grouped_tables_key_missing"
    assert not (tmp_path / "artifacts").exists()


def test_grouped_tables_refuse_an_existing_artifact_name(build_state):
    state = build_state(
        {"rows": ROWS},
        artifacts={"inventory": WorkflowArtifact(Path("inventory.txt"), datetime.now(tz=UTC))},
    )

    result = dict_list_to_grouped_tables(
        artifact_name="inventory", dict_param_name="rows", group_by="Folder", state=state
    )

    assert result.error_code == "artifact_overwritten"


def test_write_text_artifact_writes_the_value_as_it_stands(build_state, tmp_path):
    state = build_state()

    result = write_text_artifact(artifact_name="report", text="# Verdict\n\nThe test was miscalibrated.\n", state=state)

    assert result.error_code is None
    assert result.output_text == "text_artifact_created"
    assert result.artifacts["report"].relative_path == Path("report.txt")
    assert artifact_text(tmp_path, "report.txt") == "# Verdict\n\nThe test was miscalibrated.\n"


def test_write_text_artifact_refuses_a_value_that_is_not_text(build_state, tmp_path):
    state = build_state()

    result = write_text_artifact(artifact_name="report", text=["a", "b"], state=state)

    assert result.error_code == "text_artifact_not_text"
    assert not (tmp_path / "artifacts").exists()


def test_render_template_resolves_references_against_the_state(build_state, tmp_path):
    template = tmp_path / "definition" / "report.md"
    template.parent.mkdir()
    template.write_text("# Report for ${param.service}\n\nRate: ${param.rate}\n", encoding="utf-8")
    state = build_state({"service": "orders", "rate": 42}, workflow_dir=template.parent)

    result = render_template_to_artifact(artifact_name="report", template_path="report.md", state=state)

    assert result.error_code is None
    assert result.output_text == "template_rendered"
    assert result.artifacts["report"].relative_path == Path("report.md")
    assert artifact_text(tmp_path, "report.md") == "# Report for orders\n\nRate: 42\n"


def test_render_template_accepts_an_absolute_path_without_a_recorded_definition_directory(build_state, tmp_path):
    template = tmp_path / "elsewhere" / "prompt.txt"
    template.parent.mkdir()
    template.write_text("Summarize ${param.subject}.", encoding="utf-8")
    state = build_state({"subject": "the queue metrics"})

    result = render_template_to_artifact(artifact_name="prompt", template_path=str(template.absolute()), state=state)

    assert result.error_code is None
    assert artifact_text(tmp_path, "prompt.txt") == "Summarize the queue metrics."


def test_render_template_reports_an_unresolvable_relative_path(build_state):
    state = build_state()

    result = render_template_to_artifact(artifact_name="report", template_path="report.md", state=state)

    assert result.error_code == "template_path_unresolved"


def test_render_template_reports_a_missing_file(build_state, tmp_path):
    state = build_state(workflow_dir=tmp_path)

    result = render_template_to_artifact(artifact_name="report", template_path="absent.md", state=state)

    assert result.error_code == "template_not_found"


def test_render_template_reports_a_malformed_placeholder(build_state, tmp_path):
    template = tmp_path / "broken.md"
    template.write_text("Cost: $5 per run\n", encoding="utf-8")
    state = build_state(workflow_dir=tmp_path)

    result = render_template_to_artifact(artifact_name="report", template_path="broken.md", state=state)

    assert result.error_code == "template_malformed"
    assert not (tmp_path / "artifacts").exists()


def test_render_template_writes_a_file_without_references_as_it_stands(build_state, tmp_path):
    template = tmp_path / "static.md"
    template.write_text("param.service is not a reference here.\n", encoding="utf-8")
    state = build_state({"service": "orders"}, workflow_dir=tmp_path)

    result = render_template_to_artifact(artifact_name="static", template_path="static.md", state=state)

    assert result.error_code is None
    assert artifact_text(tmp_path, "static.md") == "param.service is not a reference here.\n"
