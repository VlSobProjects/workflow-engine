from datetime import UTC, datetime
from pathlib import Path

import pytest

from workflow_engine.exceptions import ArtifactNotFoundError, ArtifactPathError
from workflow_engine.models.state import (
    INVALID_WRITE_MODE,
    PARAM_OVERWRITE_FORBIDDEN,
    PARAM_TYPE_MISMATCH,
    ActionParameter,
    StateModel,
    StateReadOnlyView,
)
from workflow_engine.output import ActionNodeOutput, ParamWrite, WorkflowArtifact, WriteParamMode


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
            "test_list": ActionParameter.create(name="test_list", value=["one"], source_node_id="test_node_id"),
        },
        artifacts={
            "test_artifact": WorkflowArtifact(
                description="test_artifact",
                relative_path=Path("test/test.txt"),
                created_at=datetime.now(tz=UTC),
            ),
            "test_artifact_2": WorkflowArtifact(
                description="test_artifact",
                relative_path=Path("test/test2.txt"),
                created_at=datetime.now(tz=UTC),
            ),
        },
        current_node_id="test_node_id",
    )


@pytest.fixture
def state_read_only(state_base):
    return StateReadOnlyView.from_state(state_base)


def test_state_read_only_sync_with_state(state_base):
    read_only = StateReadOnlyView.from_state(state_base)
    for k, v in read_only.outputs().items():
        assert v == state_base.outputs[k]
    assert read_only.work_dir == state_base.work_dir
    for k, v in state_base.params.items():
        assert read_only.get_param(k) == v.value
    state_base.outputs["Node-test"] = "test"
    assert read_only.outputs().get("Node-test") == "test"


def test_state_read_only_returns_deep_copy_for_mutable_params(state_read_only, state_base):
    copied = state_read_only.get_param("test_list")
    assert copied == ["one"]
    assert copied is not None
    assert isinstance(copied, list)
    copied.append("changed")
    assert state_base.get_param("test_list", list) == ["one"]


def test_is_artifact_exist_by_name(state_read_only):
    assert state_read_only.is_artifact_exist_by_name("test_artifact")
    assert not state_read_only.is_artifact_exist_by_name("non_existent_artifact")


def test_is_artifact_exist_by_path(state_read_only):
    assert state_read_only.is_artifact_exist_by_path(Path("test/test.txt"))
    assert not state_read_only.is_artifact_exist_by_path(Path("test/non_existent.txt"))


def test_get_artifact_absolute_path(state_read_only, tmp_path):
    assert (
        state_read_only.get_artifact_absolute_path("test_artifact.txt")
        == (tmp_path / "artifacts" / "test_artifact.txt").absolute()
    )
    with pytest.raises(ArtifactPathError):
        state_read_only.get_artifact_absolute_path((tmp_path / "outside_artifact.txt").as_posix())
    assert (
        state_read_only.get_artifact_absolute_path(
            tmp_path.absolute().as_posix() + "/artifacts/test_3/test_artifact.txt"
        )
        == (tmp_path / "artifacts" / "test_3" / "test_artifact.txt").absolute()
    )


def test_get_artifact_relative_path(state_read_only, tmp_path):
    with pytest.raises(ArtifactPathError):
        state_read_only.get_artifact_absolute_path((tmp_path / "outside_artifact.txt").as_posix())

    relative_path = state_read_only.get_artifact_relative_path("test_artifact.txt")
    assert state_read_only.get_artifact_absolute_path(relative_path) == tmp_path / "artifacts" / "test_artifact.txt"


def test_get_artifact_relative_path_rejects_artifacts_root(state_read_only):
    with pytest.raises(ArtifactPathError):
        state_read_only.get_artifact_relative_path(".")


def test_artifact_name_conflict(state_base):
    state_base.update(
        curr_node_id="test_node_id",
        output=ActionNodeOutput(
            artifacts={
                "test_artifact": WorkflowArtifact(
                    description="test_artifact",
                    relative_path=Path("test/test_2.txt"),
                    created_at=datetime.now(tz=UTC),
                )
            },
            output_text="",
        ),
        save_as=None,
        next_node_id=None,
    )

    assert state_base.artifact_events[0] is not None
    assert state_base.artifact_events[0].code == "artifact_overwritten"
    assert len(state_base.artifact_events) == 1
    assert state_base.artifacts["test_artifact"].relative_path == Path("test/test_2.txt")


def test_artifact_path_conflict(state_base):
    state_base.update(
        curr_node_id="test_node_id",
        output=ActionNodeOutput(
            artifacts={
                "test_artifact_3": WorkflowArtifact(
                    description="test_artifact_3",
                    relative_path=Path("test/test2.txt"),
                    created_at=datetime.now(tz=UTC),
                )
            },
            output_text="",
        ),
        save_as=None,
        next_node_id=None,
    )

    assert state_base.artifact_events[0] is not None
    assert state_base.artifact_events[0].code == "artifact_path_conflict"
    assert len(state_base.artifact_events) == 1
    assert state_base.artifacts["test_artifact_3"].relative_path == Path("test/test2.txt")
    assert "test_artifact_2" not in state_base.artifacts


def test_artifact_reference_resolves_to_absolute_posix_path(state_base, tmp_path):
    resolved = state_base.set_parameters({"src": "artifact.test_artifact"})

    assert resolved["src"] == (tmp_path / "artifacts" / "test" / "test.txt").resolve().as_posix()


def test_artifact_reference_is_not_cached_into_params(state_base):
    state_base.set_parameters({"src": "artifact.test_artifact"})

    assert "src" not in state_base.params


def test_unknown_artifact_reference_raises_artifact_not_found(state_base):
    with pytest.raises(ArtifactNotFoundError):
        state_base.set_parameters({"src": "artifact.missing"})


def test_param_and_output_references_still_resolve(state_base):
    state_base.outputs["node_a"] = "output-value"

    resolved = state_base.set_parameters({"p": "param.test_param", "o": "output.node_a"})

    assert resolved == {"p": "string", "o": "output-value"}


def test_set_write_to_existing_param_without_overwrite_fails(state_base):
    output = ActionNodeOutput(
        output_text="ignored",
        param_writes={"test_param": ParamWrite(mode=WriteParamMode.SET, value="new_value")},
    )
    state_base.update(curr_node_id="test_node_id", output=output, save_as=None, next_node_id=None)

    assert output.error_code == PARAM_OVERWRITE_FORBIDDEN
    assert state_base.error_code == PARAM_OVERWRITE_FORBIDDEN


def test_replace_write_for_missing_param_fails(state_base):
    output = ActionNodeOutput(
        output_text="ignored",
        param_writes={"missing_param": ParamWrite(mode=WriteParamMode.REPLACE, value="new_value")},
    )
    state_base.update(curr_node_id="test_node_id", output=output, save_as=None, next_node_id=None)

    assert output.error_code == INVALID_WRITE_MODE
    assert state_base.error_code == INVALID_WRITE_MODE


def test_collection_write_type_mismatch_is_reported(state_base):
    output = ActionNodeOutput(
        output_text="ignored",
        param_writes={"test_param": ParamWrite(mode=WriteParamMode.APPEND, value="new_value")},
    )
    state_base.update(curr_node_id="test_node_id", output=output, save_as=None, next_node_id=None)

    assert output.error_code == PARAM_TYPE_MISMATCH
    assert state_base.error_code == PARAM_TYPE_MISMATCH


class TestWriteProvenance:
    """A value is recorded as produced by the node that produced it, not by the node that follows."""

    def test_a_param_write_names_the_producing_node(self, state_base):
        output = ActionNodeOutput(
            output_text="ignored",
            param_writes={"produced": ParamWrite(mode=WriteParamMode.SET, value="value")},
        )
        state_base.update(curr_node_id="PRODUCER", output=output, save_as=None, next_node_id="CONSUMER")

        assert state_base.params["produced"].source_node_id == "PRODUCER"
        assert state_base.current_node_id == "CONSUMER"

    def test_save_as_and_a_param_write_of_one_node_agree(self, state_base):
        output = ActionNodeOutput(
            output_text="text",
            param_writes={"produced": ParamWrite(mode=WriteParamMode.SET, value="value")},
        )
        state_base.update(curr_node_id="PRODUCER", output=output, save_as="saved", next_node_id="CONSUMER")

        assert state_base.params["saved"].source_node_id == state_base.params["produced"].source_node_id

    def test_an_existing_param_keeps_the_node_that_created_it(self, state_base):
        output = ActionNodeOutput(
            output_text="ignored",
            param_writes={"test_param": ParamWrite(mode=WriteParamMode.SET, value="other", allow_overwrite=True)},
        )
        state_base.update(curr_node_id="PRODUCER", output=output, save_as=None, next_node_id="CONSUMER")

        assert state_base.params["test_param"].value == "other"
        assert state_base.params["test_param"].source_node_id == "test_node_id"

    def test_an_artifact_event_names_the_producing_node(self, state_base):
        output = ActionNodeOutput(
            output_text="ignored",
            artifacts={
                "test_artifact": WorkflowArtifact(
                    description="replacement",
                    relative_path=Path("test/test.txt"),
                    created_at=datetime.now(tz=UTC),
                )
            },
        )
        state_base.update(curr_node_id="PRODUCER", output=output, save_as=None, next_node_id="CONSUMER")

        assert state_base.artifact_events[-1].node_id == "PRODUCER"
