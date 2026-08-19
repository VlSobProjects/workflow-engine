"""`append_to_param`: the accumulating half of the collection function family."""

from collections import deque
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.actions.modify_param_functions import append_to_param
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.models.state import PARAM_TYPE_MISMATCH, ActionParameter, StateModel, StateReadOnlyView


@pytest.fixture(autouse=True, scope="module")
def _components_registered(tmp_path_factory):
    create_engine(tmp_path_factory.mktemp("registration"))


def _state(tmp_path: Path, **params: object) -> StateModel:
    return StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="test",
        current_node_id="APPEND",
        session_id="test-session",
        params={
            name: ActionParameter.create(source_node_id="INIT", name=name, value=value)
            for name, value in params.items()
        },
    )


class TestAppending:
    def test_it_returns_an_append_write_for_an_existing_list(self, tmp_path):
        state = _state(tmp_path, answers=["first"])

        result = append_to_param("answers", "second", StateReadOnlyView.from_state(state))

        assert result.error_code is None
        assert result.output_text == "answers"
        write = result.param_writes["answers"]
        assert (write.mode, write.value) == (WriteParamMode.APPEND, "second")

    def test_the_write_accumulates_across_calls(self, tmp_path):
        state = _state(tmp_path, answers=[])

        for value in ("one", "two", "three"):
            output = append_to_param("answers", value, StateReadOnlyView.from_state(state))
            state.update(curr_node_id="APPEND", save_as=None, output=output, next_node_id=None)

        assert state.params["answers"].value == ["one", "two", "three"]

    def test_a_structured_value_is_appended_as_it_is(self, tmp_path):
        state = _state(tmp_path, pairs=[])

        output = append_to_param("pairs", {"q": "size?", "a": "3"}, StateReadOnlyView.from_state(state))
        state.update(curr_node_id="APPEND", save_as=None, output=output, next_node_id=None)

        assert state.params["pairs"].value == [{"q": "size?", "a": "3"}]

    def test_a_deque_parameter_is_appended_to_as_well(self, tmp_path):
        state = _state(tmp_path, queue=deque(["first"]))

        output = append_to_param("queue", "second", StateReadOnlyView.from_state(state))
        state.update(curr_node_id="APPEND", save_as=None, output=output, next_node_id=None)

        assert state.params["queue"].value == deque(["first", "second"])


class TestFailures:
    def test_a_missing_parameter_is_the_configured_error_code(self, tmp_path):
        result = append_to_param("absent", "value", StateReadOnlyView.from_state(_state(tmp_path)))

        assert result.error_code == "param_not_found"
        assert result.param_writes == {}
        assert "init_list_param" in (result.error_msg or "")

    def test_the_error_code_is_configurable(self, tmp_path):
        result = append_to_param("absent", "value", StateReadOnlyView.from_state(_state(tmp_path)), "no_accumulator")

        assert result.error_code == "no_accumulator"

    def test_a_parameter_that_cannot_be_appended_to_fails_the_write(self, tmp_path):
        # The write path owns the collection knowledge, so the type mismatch is reported there.
        state = _state(tmp_path, label="a string")

        output = append_to_param("label", "value", StateReadOnlyView.from_state(state))
        state.update(curr_node_id="APPEND", save_as=None, output=output, next_node_id=None)

        assert output.error_code == PARAM_TYPE_MISMATCH
        assert state.params["label"].value == "a string"
