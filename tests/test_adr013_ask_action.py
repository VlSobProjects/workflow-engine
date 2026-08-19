"""ADR 013: configuration, presentation and answer contract of the core `ask` action."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.actions.action_ask import DEFAULT_TITLE, AskAction
from workflow_engine.actions.base_actions import ExecutionMode
from workflow_engine.exceptions import ActionConfigurationError, WorkflowParameterError
from workflow_engine.models.state import StateModel, StateReadOnlyView
from workflow_engine.registry.action_registry import create_action, get_metadata_for_action


@pytest.fixture(autouse=True, scope="module")
def _components_registered(tmp_path_factory):
    create_engine(tmp_path_factory.mktemp("registration"))


def _state(tmp_path: Path) -> StateReadOnlyView:
    state = StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="f",
        current_node_id="ASK",
        session_id="s",
    )
    state.add_parameter("candidate", "report.csv")
    state.add_parameter("candidate_path", Path("C:/reports/candidate.csv"))
    state.outputs["PREVIOUS"] = "42 rows"
    return StateReadOnlyView.from_state(state)


def _ask(**parameters) -> AskAction:
    return AskAction({"instruction": "Decide", "answer": [], **parameters})


class TestRegistration:
    def test_the_action_is_registered_as_interactive(self):
        action = create_action("ask", {"instruction": "Decide", "answer": []})
        assert isinstance(action, AskAction)
        assert action.execution_mode() is ExecutionMode.INTERACTIVE

    def test_it_carries_operator_metadata(self):
        metadata = get_metadata_for_action("ask")
        assert metadata is not None
        assert "answer" in metadata.required_parameters
        assert metadata.examples


class TestConfiguration:
    def test_the_answer_declaration_is_required(self):
        with pytest.raises(ActionConfigurationError):
            AskAction({"instruction": "Decide"})

    def test_an_empty_declaration_asks_without_binding_anything(self):
        assert _ask().answer_contract().declarations == ()

    def test_the_instruction_is_required(self):
        with pytest.raises(WorkflowParameterError):
            AskAction({"answer": []})

    def test_the_declaration_shares_the_inputs_validator(self):
        action = _ask(answer=[{"name": "depth", "type": "int"}])
        (declaration,) = action.answer_contract().declarations
        assert (declaration.name, declaration.type, declaration.required) == ("depth", "builtins.int", True)

    def test_a_malformed_declaration_is_a_configuration_error(self):
        with pytest.raises(Exception, match="answer"):
            _ask(answer=[{"name": "1bad"}])

    def test_a_list_field_must_hold_strings(self):
        with pytest.raises(ActionConfigurationError):
            _ask(options=[1, 2])

    def test_the_error_catalogue_must_map_strings(self):
        with pytest.raises(ActionConfigurationError):
            _ask(errors={"code": 5})


class TestPresentation:
    def test_defaults_keep_the_node_short(self, tmp_path):
        response = _ask().present(_state(tmp_path))
        assert response.title == DEFAULT_TITLE
        assert response.description == "Decide"
        assert response.instruction == "Decide"
        assert response.errors is None

    def test_references_are_resolved_in_strings_and_in_list_entries(self, tmp_path):
        response = _ask(context="param.candidate", hints=["output.PREVIOUS", "plain hint"]).present(_state(tmp_path))
        assert response.context == "report.csv"
        assert response.hints == ["42 rows", "plain hint"]

    def test_a_path_value_is_rendered_in_posix_form(self, tmp_path):
        # The presentation is published in the command result, so ADR 008 holds for it too.
        response = _ask(context="param.candidate_path").present(_state(tmp_path))
        assert response.context == "C:/reports/candidate.csv"

    def test_the_declaration_travels_with_the_presentation(self, tmp_path):
        response = _ask(answer=[{"name": "reviewer"}], errors={"nope": "cannot"}).present(_state(tmp_path))
        assert response.answer is not None
        assert [declaration.name for declaration in response.answer.declarations] == ["reviewer"]
        assert response.answer.declared_codes() == frozenset({"nope"})

    def test_the_error_catalogue_is_not_reported_as_a_failure(self, tmp_path):
        # `PresentResponse.errors` says what failed; the catalogue says what may fail. See ADR 013 §2.
        response = _ask(errors={"nope": "cannot"}).present(_state(tmp_path))
        assert response.errors is None
