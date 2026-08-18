from datetime import UTC, datetime

import pytest

from workflow_engine.actions.create_artifact_functions import dict_list_to_pretty_table
from workflow_engine.models.state import ActionParameter, StateModel, StateReadOnlyView


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
