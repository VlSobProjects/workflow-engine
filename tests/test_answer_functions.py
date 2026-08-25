"""The core pair that computes on an accepted answer: `echo_answer` and `collect_answer`.

ADR 015 shipped the stage without components for it. These two are what a data-only node next to a
question used to do, and the end-to-end proof that they carry it is the ADR-0083 scenario, which runs
both through the CLI (`tests/test_adr0083_coverage.py`).
"""

from collections import deque
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.actions.answer_functions import ANSWER_VALUE_MISSING, collect_answer, echo_answer
from workflow_engine.collection_param_handlers import PARAM_TYPE_MISMATCH, WriteParamMode
from workflow_engine.models.state import ActionParameter, StateModel, StateReadOnlyView
from workflow_engine.output import ActionNodeOutput


@pytest.fixture(autouse=True, scope="module")
def _components_registered(tmp_path_factory):
    create_engine(tmp_path_factory.mktemp("registration"))


def _state(tmp_path: Path, **params: object) -> StateReadOnlyView:
    state = StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="test",
        current_node_id="ASK",
        session_id="test-session",
        params={
            name: ActionParameter.create(source_node_id="INIT", name=name, value=value)
            for name, value in params.items()
        },
    )
    return StateReadOnlyView.from_state(state)


def _answer(text: str = "", **values: object) -> ActionNodeOutput:
    """The output an accepted answer arrives as: its text, and its values still on their way to the bus."""
    output = ActionNodeOutput(output_text=text)
    for name, value in values.items():
        output.set_param(name, value)
    return output


class TestEchoAnswer:
    def test_the_answered_value_becomes_the_output_text(self):
        assert echo_answer("decision", _answer(decision="approved")).output_text == "approved"

    def test_the_answer_keeps_its_writes(self):
        answered = _answer("said something", decision="approved")

        result = echo_answer("decision", answered)

        assert result is answered, "a fresh output would drop the answered values"
        assert result.get_param("decision") == "approved"

    def test_a_path_is_surfaced_in_posix_form(self):
        result = echo_answer("root", _answer(root=Path("C:/data/candidate")))

        assert result.output_text == "C:/data/candidate"

    def test_a_collection_is_surfaced_as_compact_json(self):
        result = echo_answer("issues", _answer(issues=["no changelog entry", "version not bumped"]))

        assert result.output_text == '["no changelog entry","version not bumped"]'

    def test_a_name_the_answer_does_not_carry_is_an_error(self):
        result = echo_answer("decision", _answer("approved"))

        assert result.error_code == ANSWER_VALUE_MISSING
        assert result.output_text == ""

    def test_a_refused_answer_still_carries_the_values_it_did_bring(self):
        """The node fails; the answer it accepted is not unmade. See the engine's own ordering."""
        result = echo_answer("decision", _answer("approved", reviewer="agent:test"))

        assert result.error_code == ANSWER_VALUE_MISSING
        assert result.get_param("reviewer") == "agent:test"

    def test_the_error_code_is_configurable(self):
        result = echo_answer("decision", _answer("approved"), error_not_answered="no_decision")

        assert result.error_code == "no_decision"


class TestCollectAnswer:
    def test_the_answer_text_is_appended_when_no_name_is_declared(self, tmp_path):
        result = collect_answer("qa_log", 2, _answer("first"), _state(tmp_path, qa_log=[]))

        write = result.param_writes["qa_log"]
        assert (write.mode, write.value) == (WriteParamMode.APPEND, "first")

    def test_a_declared_value_is_appended_when_it_is_named(self, tmp_path):
        pair = {"question": "size?", "answer": "3"}

        result = collect_answer("qa_log", 2, _answer("reported", qa_pair=pair), _state(tmp_path, qa_log=[]), "qa_pair")

        assert result.param_writes["qa_log"].value == pair
        assert result.get_param("qa_pair") == pair, "the answered value still lands on the bus"

    def test_it_reports_more_while_the_minimum_is_not_reached(self, tmp_path):
        assert collect_answer("qa_log", 2, _answer("first"), _state(tmp_path, qa_log=[])).output_text == "more"

    def test_it_reports_enough_on_the_pass_that_reaches_the_minimum(self, tmp_path):
        """The pending item counts: the check holds on the pass that adds it, not one pass later."""
        state = _state(tmp_path, qa_log=["first"])

        assert collect_answer("qa_log", 2, _answer("second"), state).output_text == "enough"

    def test_both_texts_are_configurable(self, tmp_path):
        state = _state(tmp_path, qa_log=[])

        result = collect_answer("qa_log", 2, _answer("first"), state, enough="done", more="again")

        assert result.output_text == "again"

    def test_a_deque_is_counted_the_same_way(self, tmp_path):
        state = _state(tmp_path, qa_log=deque(["first", "second"]))

        assert collect_answer("qa_log", 2, _answer("third"), state).output_text == "enough"

    def test_a_parameter_that_does_not_exist_is_an_error(self, tmp_path):
        result = collect_answer("qa_log", 2, _answer("first", qa_pair={"question": "size?"}), _state(tmp_path))

        assert result.error_code == "param_not_found"
        assert "qa_log" not in result.param_writes
        assert result.get_param("qa_pair") == {"question": "size?"}, "the accepted answer still lands"

    def test_a_parameter_that_cannot_be_counted_is_a_type_mismatch(self, tmp_path):
        result = collect_answer("qa_log", 2, _answer("first"), _state(tmp_path, qa_log=7))

        assert result.error_code == PARAM_TYPE_MISMATCH

    def test_a_declared_name_the_answer_does_not_carry_is_an_error(self, tmp_path):
        result = collect_answer("qa_log", 2, _answer("first"), _state(tmp_path, qa_log=[]), "qa_pair")

        assert result.error_code == ANSWER_VALUE_MISSING
        assert "qa_log" not in result.param_writes
