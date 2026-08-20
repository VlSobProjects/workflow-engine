"""ADR 016: references resolve inside the text of a field declared as template text.

The `ask` presentation is the declared template set (§1a), a malformed template fails the node when
it is built and an unresolved reference fails the run at presentation (§2), and a collection reaches
the text as compact JSON (§3).
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from tests.test_engine_transitions import engine_for
from workflow_engine.actions.action_ask import AskAction
from workflow_engine.exceptions import ActionConfigurationError, ArtifactNotFoundError, StateLoadParameterError
from workflow_engine.models.state import StateModel, StateReadOnlyView
from workflow_engine.output import WorkflowArtifact
from workflow_engine.registry.action_registry import get_metadata_for_action

TEMPLATE_FIELDS = (
    "title",
    "description",
    "instruction",
    "goal",
    "context",
    "options",
    "requirements",
    "constraints",
    "examples",
    "hints",
)


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
    state.add_parameter("root", Path("C:/reports"))
    state.add_parameter("issues", ["missing header", "empty row"])
    state.add_parameter("counts", {"rows": 2, "columns": 3})
    state.outputs["SCAN"] = "42 rows"
    state.artifacts["report_csv"] = WorkflowArtifact(relative_path=Path("out/report.csv"), created_at=state.timestamp)
    return StateReadOnlyView.from_state(state)


def _ask(**parameters) -> AskAction:
    return AskAction({"instruction": "Decide", "answer": [], **parameters})


def _ask_node(**parameters) -> dict[str, object]:
    return {
        "id": "ASK",
        "action_type": "ask",
        "action_parameters": {"instruction": "Decide", "answer": [], **parameters},
        "transitions": [{"stop": True}],
    }


class TestBuildTime:
    """A malformed template is a configuration error of the node, found without any state. See §2."""

    @pytest.mark.parametrize(
        "text",
        [
            "$param.root",
            "costs $5",
            "a lone $",
            "${param.root",
            "${}",
            "${param.}",
        ],
    )
    def test_a_malformed_placeholder_refuses_the_node(self, text):
        with pytest.raises(ActionConfigurationError, match="template text"):
            _ask(instruction=text)

    def test_an_unknown_prefix_is_not_a_reference(self):
        with pytest.raises(ActionConfigurationError, match="not a reference"):
            _ask(instruction="Run it in ${HOME}")

    def test_a_list_entry_is_checked_as_its_own_field(self):
        with pytest.raises(ActionConfigurationError, match=r"hints\[1\]"):
            _ask(hints=["fine", "$5 per row"])

    def test_the_instruction_is_named_by_the_error(self):
        # `description` defaults to the instruction string, so the commonest shape is a templated
        # instruction and no description; both are template text for exactly that reason. See §1a.
        with pytest.raises(ActionConfigurationError, match="'instruction'"):
            _ask(instruction="$5")

    def test_every_presentation_field_accepts_a_template(self):
        action = _ask(
            title="${param.root}",
            description="${param.root}",
            instruction="${param.root}",
            goal="${param.root}",
            context="${param.root}",
            **{key: ["${param.root}"] for key in ("options", "requirements", "constraints", "examples", "hints")},
        )
        assert action.instruction == "${param.root}"

    def test_an_escaped_delimiter_writes_a_literal_dollar(self, tmp_path):
        response = _ask(instruction="Costs $$5 per row").present(_state(tmp_path))
        assert response.instruction == "Costs $5 per row"

    def test_the_engine_reports_it_with_the_other_node_errors(self, tmp_path):
        # The node is built before the run starts, so the error joins the per-node aggregation of
        # ADR 001 instead of surfacing inside a published question.
        response, _ = engine_for(create_engine(tmp_path), tmp_path / "run", [_ask_node(instruction="$5")])
        assert response.errors
        assert "template text" in response.errors["ASK"]


class TestPresentation:
    """The references resolve when the presentation is built, from the state view. See §4."""

    def test_a_reference_stands_inside_the_sentence(self, tmp_path):
        response = _ask(instruction="Check the folder ${param.root} and answer").present(_state(tmp_path))
        assert response.instruction == "Check the folder C:/reports and answer"

    def test_all_three_reference_kinds_resolve(self, tmp_path):
        response = _ask(instruction="${param.root} then ${output.SCAN} then ${artifact.report_csv}").present(
            _state(tmp_path)
        )
        artifact_path = (tmp_path / "artifacts" / "out" / "report.csv").as_posix()
        assert response.instruction == f"C:/reports then 42 rows then {artifact_path}"

    def test_a_list_renders_as_compact_json_inside_the_text(self, tmp_path):
        response = _ask(instruction="Fix ${param.issues}").present(_state(tmp_path))
        assert response.instruction == 'Fix ["missing header","empty row"]'

    def test_a_dict_renders_as_compact_json_inside_the_text(self, tmp_path):
        response = _ask(instruction="Table ${param.counts}").present(_state(tmp_path))
        assert response.instruction == 'Table {"rows":2,"columns":3}'

    def test_a_list_field_is_templated_per_entry(self, tmp_path):
        response = _ask(hints=["under ${param.root}", "plain hint"]).present(_state(tmp_path))
        assert response.hints == ["under C:/reports", "plain hint"]

    def test_the_default_description_carries_the_rendered_instruction(self, tmp_path):
        response = _ask(instruction="Check ${param.root}").present(_state(tmp_path))
        assert response.description == "Check C:/reports"

    def test_a_whole_field_reference_keeps_working(self, tmp_path):
        # Today's form: a field that *is* a reference, with no delimiter anywhere. See §1.
        response = _ask(context="param.root").present(_state(tmp_path))
        assert response.context == "C:/reports"

    def test_a_bare_context_list_also_renders_as_json(self, tmp_path):
        # §3 applies to the whole-value form as well, template or not.
        response = _ask(context="param.issues").present(_state(tmp_path))
        assert response.context == '["missing header","empty row"]'

    def test_text_that_only_looks_like_a_reference_stays_literal(self, tmp_path):
        response = _ask(instruction="write param.root in the answer").present(_state(tmp_path))
        assert response.instruction == "write param.root in the answer"

    def test_re_presenting_shows_the_same_values(self, tmp_path):
        # A plain `resume` re-presents the question, and resolution is a pure function of the state,
        # so no user code runs and the answerer sees what the journal recorded. See ADR 013 §6.
        action = _ask(instruction="Check ${param.root}")
        state = _state(tmp_path)
        assert action.present(state).instruction == action.present(state).instruction


class TestUnresolvedReference:
    """An unresolved reference fails the run at the question, in the error class it always used."""

    def test_a_missing_parameter_fails_the_presentation(self, tmp_path):
        with pytest.raises(StateLoadParameterError):
            _ask(instruction="Check ${param.rooot}").present(_state(tmp_path))

    def test_a_missing_output_fails_the_presentation(self, tmp_path):
        with pytest.raises(StateLoadParameterError):
            _ask(instruction="Check ${output.NOWHERE}").present(_state(tmp_path))

    def test_a_missing_artifact_fails_the_presentation(self, tmp_path):
        with pytest.raises(ArtifactNotFoundError):
            _ask(instruction="Read ${artifact.nothing}").present(_state(tmp_path))

    def test_it_never_reaches_the_answerer_as_written(self, tmp_path):
        with pytest.raises(StateLoadParameterError):
            _ask(context="${param.rooot}").present(_state(tmp_path))


class TestOperatorHelp:
    """An author sees which fields are template text on the ADR 009 surface."""

    def test_every_presentation_field_is_declared_template_text(self):
        metadata = get_metadata_for_action("ask")
        assert metadata is not None
        declared = {**metadata.required_parameters, **metadata.optional_parameters}
        assert {name for name, doc in declared.items() if doc.template} == set(TEMPLATE_FIELDS)

    def test_the_answer_and_function_keys_are_not_templates(self):
        metadata = get_metadata_for_action("ask")
        assert metadata is not None
        declared = {**metadata.required_parameters, **metadata.optional_parameters}
        assert not declared["answer"].template
        assert not declared["function_parameters"].template
