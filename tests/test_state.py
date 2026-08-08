from datetime import datetime,UTC
from pathlib import Path

import pytest

from workflow_engine.exceptions import ArtifactPathError
from workflow_engine.models.state import StateReadOnlyView, ActionParameter, StateModel
from workflow_engine.output import WorkflowArtifact, ActionNodeOutput


@pytest.fixture
def state_base(tmp_path):
    return StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="test",
        session_id="test-session-id",
        params={
            "test_param": ActionParameter.create(name="test_param", value="string", source_node_id="test_node_id"),
            "test_param2": ActionParameter.create(
                name="test_param2", value="new_string2", source_node_id="test_node_id"
            ),
        },
        artifacts={
            "test_artifact":WorkflowArtifact(
                description="test_artifact",
                relative_path=Path("/test/test.txt"),
                created_at=datetime.now(tz=UTC)
            ),
            "test_artifact_2": WorkflowArtifact(
                description="test_artifact",
                relative_path=Path("/test/test2.txt"),
                created_at=datetime.now(tz=UTC)
            ),

        },
        current_node_id="test_node_id",
    )


@pytest.fixture
def state_read_only(state_base):
    return StateReadOnlyView.from_state(state_base)

def test_state_read_only_sinc_with_state(state_base):
    read_only = StateReadOnlyView.from_state(state_base)
    for k,v in read_only.outputs().items():
        assert v == state_base.outputs[k]
    assert read_only.work_dir == state_base.work_dir
    for k,v in state_base.params.items():
        assert read_only.get_param(k) == v.value
    state_base.outputs["Node-test"] = "test"
    assert read_only.outputs().get("Node-test") == "test"

def test_is_artifact_exist_by_name(state_read_only):
    assert state_read_only.is_artifact_exist_by_name("test_artifact")
    assert not state_read_only.is_artifact_exist_by_name("non_existent_artifact")


def test_is_artifact_exist_by_path(state_read_only):
    assert state_read_only.is_artifact_exist_by_path(Path("/test/test.txt"))
    assert not state_read_only.is_artifact_exist_by_path(Path("/test/non_existent.txt"))


def test_get_artifact_absolute_path(state_read_only, tmp_path):
    assert state_read_only.get_artifact_absolute_path("test_artifact.txt") == (tmp_path / "artifacts" / "test_artifact.txt").absolute()
    with pytest.raises(ArtifactPathError):
        state_read_only.get_artifact_absolute_path("C:/non_existent_artifact.txt")
    assert state_read_only.get_artifact_absolute_path(tmp_path.absolute().as_posix()+"/artifacts/test_3/test_artifact.txt") == (tmp_path / "artifacts" / "test_3" /"test_artifact.txt").absolute()


def test_get_artifact_relative_path(state_read_only, tmp_path):
    with pytest.raises(ArtifactPathError):
        state_read_only.get_artifact_absolute_path("C:/non_existent_artifact.txt")

    relative_path = state_read_only.get_artifact_relative_path("test_artifact.txt")
    assert state_read_only.get_artifact_absolute_path(relative_path) == tmp_path / "artifacts" / "test_artifact.txt"


def test_artifact_name_conflict(state_base):
    state_base.update(
        curr_node_id="test_node_id",
        output=ActionNodeOutput(
            artifacts={
                "test_artifact":WorkflowArtifact(
                    description="test_artifact",
                    relative_path=Path("/test/test_2.txt"),
                    created_at=datetime.now(tz=UTC)
                )
            },
            output_text=""
        ),
        save_as=None,
        next_node_id=None
    )

    assert state_base.artifact_events[0]
    assert state_base.artifact_events[0].code == "artifact_overwritten"
    assert len(state_base.artifact_events) == 1
    assert state_base.artifacts["test_artifact"].relative_path == Path("/test/test_2.txt")


def test_artifact_path_conflict(state_base):
    state_base.update(
        curr_node_id="test_node_id",
        output=ActionNodeOutput(
            artifacts={
                "test_artifact_3":WorkflowArtifact(
                    description="test_artifact_3",
                    relative_path=Path("/test/test2.txt"),
                    created_at=datetime.now(tz=UTC)
                )
            },
            output_text=""
        ),
        save_as=None,
        next_node_id=None
    )

    assert state_base.artifact_events[0]
    assert state_base.artifact_events[0].code == "artifact_path_conflict"
    assert len(state_base.artifact_events) == 1
    assert state_base.artifacts["test_artifact_3"].relative_path == Path("/test/test2.txt")
