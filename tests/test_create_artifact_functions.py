from datetime import UTC, datetime
from pathlib import Path

import pytest

from workflow_engine.actions.create_artifact_functions import copy_artifact, dict_list_to_pretty_table
from workflow_engine.models.state import ActionParameter, StateModel, StateReadOnlyView
from workflow_engine.output import WorkflowArtifact


@pytest.fixture
def state_with_list(tmp_path):
    def build(value):
        state = StateModel(
            timestamp=datetime.now(tz=UTC),
            work_dir=tmp_path,
            schema_version="1",
            flow_id="test",
            session_id="test-session-id",
            params={
                "rows": ActionParameter.create(name="rows", value=value, source_node_id="test_node_id"),
            },
            artifacts={},
            current_node_id="test_node_id",
        )
        return StateReadOnlyView.from_state(state)

    return build


def test_empty_list_returns_no_data_without_crash(state_with_list, tmp_path):
    state = state_with_list([])

    result = dict_list_to_pretty_table(artifact_name="table", dict_param_name="rows", state=state)

    assert result.error_code == "pretty_table_no_data"
    assert result.artifacts == {}
    assert not (tmp_path / "artifacts").exists()


def test_non_list_param_returns_no_data(state_with_list):
    state = state_with_list("not-a-list")

    result = dict_list_to_pretty_table(artifact_name="table", dict_param_name="rows", state=state)

    assert result.error_code == "pretty_table_no_data"


def test_non_empty_list_creates_artifact(state_with_list, tmp_path):
    state = state_with_list([{"Path": "a.txt", "Size": "1"}])

    result = dict_list_to_pretty_table(artifact_name="table", dict_param_name="rows", state=state)

    assert result.error_code is None
    assert result.output_text == "pretty_table_created"
    assert "table" in result.artifacts
    assert (tmp_path / "artifacts" / "table.txt").is_file()


@pytest.fixture
def state_with_artifact(tmp_path):
    source_file = tmp_path / "artifacts" / "src" / "report.csv"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("col\n1\n")
    state = StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="test",
        session_id="test-session-id",
        params={},
        artifacts={
            "source": WorkflowArtifact(
                relative_path=Path("src/report.csv"),
                created_at=datetime.now(tz=UTC),
                description="source",
            )
        },
        current_node_id="test_node_id",
    )
    return StateReadOnlyView.from_state(state)


def test_copy_artifact_default_target_path_uses_source_suffix(state_with_artifact, tmp_path):
    result = copy_artifact(source_artifact_name="source", target_artifact_name="promoted", state=state_with_artifact)

    assert result.error_code is None
    assert result.output_text == "artifact_copied"
    assert result.artifacts["promoted"].relative_path == Path("promoted.csv")
    assert (tmp_path / "artifacts" / "promoted.csv").is_file()


def test_copy_artifact_explicit_target_path(state_with_artifact, tmp_path):
    result = copy_artifact(
        source_artifact_name="source",
        target_artifact_name="promoted",
        state=state_with_artifact,
        target_path="out/final.csv",
    )

    assert result.error_code is None
    assert result.artifacts["promoted"].relative_path == Path("out/final.csv")
    assert (tmp_path / "artifacts" / "out" / "final.csv").is_file()


def test_copy_artifact_unknown_source_returns_not_found(state_with_artifact):
    result = copy_artifact(source_artifact_name="missing", target_artifact_name="promoted", state=state_with_artifact)

    assert result.error_code == "artifact_not_found"
    assert result.artifacts == {}


def test_copy_artifact_refuses_existing_target_name(state_with_artifact):
    result = copy_artifact(
        source_artifact_name="source",
        target_artifact_name="source",
        state=state_with_artifact,
        target_path="out/other.csv",
    )

    assert result.error_code == "artifact_overwritten"


def test_copy_artifact_refuses_conflicting_target_path(state_with_artifact):
    result = copy_artifact(
        source_artifact_name="source",
        target_artifact_name="promoted",
        state=state_with_artifact,
        target_path="src/report.csv",
    )

    assert result.error_code == "artifact_path_conflict"


def test_copy_artifact_allow_overwrite_proceeds(state_with_artifact, tmp_path):
    result = copy_artifact(
        source_artifact_name="source",
        target_artifact_name="source",
        state=state_with_artifact,
        target_path="out/other.csv",
        allow_overwrite=True,
    )

    assert result.error_code is None
    assert result.artifacts["source"].relative_path == Path("out/other.csv")
    assert (tmp_path / "artifacts" / "out" / "other.csv").is_file()
