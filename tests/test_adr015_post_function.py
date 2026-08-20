"""ADR 015: a registered function computing on an accepted answer inside the interactive node.

The functions registered here are test-only on purpose. The branch ships the mechanism, not a library
of functions for it, so what a post function does is written where it is used, the way an external
module would write its own.

The end-to-end cases drive the CLI, because the stage sits between the answer and the transition and
only a real run puts it there: the state view it reads is the one the guards read, and the output it
returns is the one the engine applies.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, cast

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.actions.action_ask import AskAction
from workflow_engine.cli.main import main
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.exceptions import ActionConfigurationError
from workflow_engine.models.state import SessionEventCode, StateModel, StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.function_registry import register_function
from workflow_engine.tools import render_value_as_text

POST_FAILED = "post_failed"


@register_function(summary="Test only: put a declared answer value into the output text.")
def adr015_surface_answer(
    name: Annotated[str, "Declared answer name to surface as the output text"],
    output: Annotated[ActionNodeOutput, "The accepted answer, injected by the engine"],
) -> ActionNodeOutput:
    """Make a declared answer value routable without a node whose only job is to echo it."""
    output.output_text = render_value_as_text(output.get_param(name, ""))
    return output


@register_function(summary="Test only: normalize a declared answer value in place.")
def adr015_normalize_answer(
    name: Annotated[str, "Declared answer name to normalize"],
    output: Annotated[ActionNodeOutput, "The accepted answer, injected by the engine"],
) -> ActionNodeOutput:
    """Trim and lower-case what was answered, so a nearly-right reply still decides."""
    normalized = str(output.get_param(name, "")).strip().lower()
    output.set_param(name, normalized)
    output.output_text = normalized
    return output


@register_function(summary="Test only: accumulate the answer and report whether the loop has enough.")
def adr015_collect_answer(
    param_name: Annotated[str, "Existing list parameter the answer text is appended to"],
    minimum: Annotated[int, "How many answers the loop needs"],
    output: Annotated[ActionNodeOutput, "The accepted answer, injected by the engine"],
    state: Annotated[StateReadOnlyView, "Read-only state view, injected by the engine"],
) -> ActionNodeOutput:
    """Accumulate in the node that asked and route on 'enough' there as well.

    Both halves of the two-node workaround at once: the append that a following node used to make,
    and the check that the head of the loop used to make. The APPEND write stays spelled out.
    """
    collected = state.get_param(param_name)
    if not isinstance(collected, list):
        return ActionNodeOutput(
            output_text="",
            error_code="param_not_found",
            error_msg=f"Parameter '{param_name}' is not a list parameter",
        )
    output.param_writes[param_name] = ParamWrite(mode=WriteParamMode.APPEND, value=output.output_text)
    output.output_text = "enough" if len(collected) + 1 >= minimum else "more"
    return output


@register_function(summary="Test only: refuse the answer with an error code.")
def adr015_refuse_answer(
    code: Annotated[str, "Error code the function reports"],
) -> ActionNodeOutput:
    """Report a failure the way any registered function does."""
    return ActionNodeOutput(output_text="", error_code=code, error_msg="the post function refused the answer")


@register_function(summary="Test only: return a fresh output instead of the one it was given.")
def adr015_replace_output(
    text: Annotated[str, "Text of the fresh output"],
) -> ActionNodeOutput:
    """Discard the answer's writes: the function's result is the node output, all of it."""
    return ActionNodeOutput(output_text=text)


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
    return StateReadOnlyView.from_state(state)


def _ask(**parameters) -> AskAction:
    return AskAction({"instruction": "Decide", "answer": [], **parameters})


class TestConfiguration:
    def test_a_question_without_a_function_stays_declarative(self):
        assert _ask().registered_function is None

    def test_the_function_is_resolved_at_configuration_time(self):
        action = _ask(function_name="adr015_refuse_answer", function_parameters={"code": POST_FAILED})
        assert action.registered_function is not None

    def test_an_unregistered_function_is_a_configuration_error(self):
        with pytest.raises(ActionConfigurationError):
            _ask(function_name="no_such_function")

    def test_parameters_without_a_function_are_refused_rather_than_ignored(self):
        with pytest.raises(ActionConfigurationError, match="function_parameters"):
            _ask(function_parameters={"code": POST_FAILED})


class TestTheStage:
    def test_a_question_without_a_function_returns_the_answer_unchanged(self, tmp_path):
        answered = ActionNodeOutput(output_text="approved")
        assert _ask().process_answer(_state(tmp_path), answered) is answered

    def test_a_failure_answer_never_reaches_the_function(self, tmp_path):
        action = _ask(function_name="adr015_refuse_answer", function_parameters={"code": POST_FAILED})
        refused = ActionNodeOutput(output_text="", error_code="answer_failed", error_msg="no decision")

        result = action.process_answer(_state(tmp_path), refused)

        assert (result.error_code, result.error_msg) == ("answer_failed", "no decision")

    def test_the_result_of_the_function_is_what_comes_back(self, tmp_path):
        action = _ask(function_name="adr015_surface_answer", function_parameters={"name": "decision"})
        answered = ActionNodeOutput(output_text="")
        answered.set_param("decision", "approved")

        assert action.process_answer(_state(tmp_path), answered).output_text == "approved"


def _workflow(ask_node: dict[str, object], *, before: list[dict[str, object]] | None = None) -> dict[str, object]:
    """One flow around the node under test: whatever it needs first, the question, and two ends."""
    return {
        "schema_version": "1",
        "flow_id": "adr015-post-function",
        "start_node_id": (before[0]["id"] if before else ask_node["id"]),
        "nodes": [
            *(before or []),
            ask_node,
            {
                "id": "DONE",
                "action_type": "stop",
                "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "done"}},
            },
            {
                "id": "RECOVER",
                "action_type": "stop",
                "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "recovered"}},
            },
        ],
    }


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, str]:
    config = tmp_path / "workflow_engine_config.json"
    config.write_text(
        json.dumps({"work_dir": (tmp_path / "runtime").as_posix(), "external_modules": [], "storage": {}})
    )
    return {
        "config": config.as_posix(),
        "workflow": (tmp_path / "flow.json").as_posix(),
        "runtime": (tmp_path / "runtime").as_posix(),
    }


def start(workspace: dict[str, str], workflow: dict[str, object], capsys) -> str:
    Path(workspace["workflow"]).write_text(json.dumps(workflow), encoding="utf-8")
    code, response = run_json_cli(
        ["run", "--workflow-file", workspace["workflow"], "--config", workspace["config"]], capsys
    )
    assert code == 2, "the flow must stop at its question"
    return cast(str, response["session_id"])


def answer(workspace: dict[str, str], session_id: str, capsys, *values: str) -> tuple[int, dict[str, object]]:
    argv = ["resume", "--session-id", session_id, "--config", workspace["config"]]
    return run_json_cli([*argv, *values], capsys)


def success(values: dict[str, object], text: str = "") -> list[str]:
    return ["--answer", json.dumps({"status": "success", "values": values, "text": text, "actor": "agent:test"})]


def state_of(workspace: dict[str, str], session_id: str) -> dict[str, object]:
    path = Path(workspace["runtime"]) / "json-storage" / session_id / "state.json"
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def param_of(state: dict[str, object], name: str) -> object:
    return cast(dict, cast(dict, cast(dict, state["params"])[name])["value"])["object"]


class TestThroughTheEngine:
    def test_an_answered_value_routes_the_node_that_asked_for_it(self, workspace, capsys):
        flow = _workflow(
            {
                "id": "ASK",
                "action_type": "ask",
                "action_parameters": {
                    "instruction": "Decide",
                    "answer": [{"name": "decision"}],
                    "function_name": "adr015_surface_answer",
                    "function_parameters": {"name": "decision"},
                },
                "save_as": "routed_on",
                "transitions": [{"next": "DONE", "validator": {"equals": "approved"}}, {"next": "RECOVER"}],
            }
        )
        session_id = start(workspace, flow, capsys)

        code, _ = answer(workspace, session_id, capsys, *success({"decision": "approved"}))

        assert code == 0
        state = state_of(workspace, session_id)
        assert cast(dict, state["outputs"])["DONE"] == "done"
        # `save_as` keeps what the node produced, which is now the text of the function.
        assert param_of(state, "routed_on") == "approved"
        assert param_of(state, "decision") == "approved"

    def test_the_node_that_asks_accumulates_its_own_answers_and_decides_when_to_leave(self, workspace, capsys):
        flow = _workflow(
            {
                "id": "ASK",
                "action_type": "ask",
                "action_parameters": {
                    "instruction": "Ask the next question",
                    "answer": [],
                    "function_name": "adr015_collect_answer",
                    "function_parameters": {"param_name": "answers", "minimum": 2},
                },
                "transitions": [{"next": "DONE", "validator": {"equals": "enough"}}, {"next": "ASK"}],
            },
            before=[
                {
                    "id": "INIT",
                    "action_type": "function",
                    "action_parameters": {
                        "function_name": "init_list_param",
                        "function_parameters": {"param_name": "answers"},
                    },
                    "transitions": [{"next": "ASK"}],
                }
            ],
        )
        session_id = start(workspace, flow, capsys)

        code, _ = answer(workspace, session_id, capsys, *success({}, text="first"))
        assert code == 2, "the loop comes back to the question until it has enough"

        code, _ = answer(workspace, session_id, capsys, *success({}, text="second"))

        assert code == 0
        state = state_of(workspace, session_id)
        stored = cast(list, param_of(state, "answers"))
        assert [cast(dict, item)["object"] for item in stored] == ["first", "second"]

    def test_a_normalized_value_lands_on_the_bus_while_the_journal_records_what_was_supplied(self, workspace, capsys):
        flow = _workflow(
            {
                "id": "ASK",
                "action_type": "ask",
                "action_parameters": {
                    "instruction": "Decide",
                    "answer": [{"name": "decision"}],
                    "function_name": "adr015_normalize_answer",
                    "function_parameters": {"name": "decision"},
                },
                "transitions": [{"next": "DONE", "validator": {"equals": "approved"}}, {"next": "RECOVER"}],
            }
        )
        session_id = start(workspace, flow, capsys)

        code, _ = answer(workspace, session_id, capsys, *success({"decision": "  APPROVED  "}))

        assert code == 0
        state = state_of(workspace, session_id)
        assert param_of(state, "decision") == "approved"
        answered = [
            event
            for event in cast(list, state["session_events"])
            if cast(dict, event)["code"] == SessionEventCode.INTERACTIVE_ANSWERED.value
        ]
        details = cast(dict, cast(dict, answered[-1])["details"])
        assert details["names"] == ["decision"]
        assert details["actor"] == "agent:test"

    def test_a_failing_function_fails_the_node_under_its_own_code(self, workspace, capsys):
        flow = _workflow(
            {
                "id": "ASK",
                "action_type": "ask",
                "action_parameters": {
                    "instruction": "Decide",
                    "answer": [],
                    "function_name": "adr015_refuse_answer",
                    "function_parameters": {"code": POST_FAILED},
                },
                "transitions": [{"next": "DONE", "validator": {"equals": "approved"}}],
            }
        )
        session_id = start(workspace, flow, capsys)

        code, response = answer(workspace, session_id, capsys, *success({}, text="approved"))

        assert code == 3
        assert POST_FAILED in json.dumps(response["errors"])
        assert cast(dict, state_of(workspace, session_id)["errors"])["ASK"].count(POST_FAILED) == 1

    def test_a_failing_function_routes_like_any_other_node_error(self, workspace, capsys):
        flow = _workflow(
            {
                "id": "ASK",
                "action_type": "ask",
                "action_parameters": {
                    "instruction": "Decide",
                    "answer": [],
                    "function_name": "adr015_refuse_answer",
                    "function_parameters": {"code": POST_FAILED},
                },
                "transitions": [{"next": "RECOVER", "errors": [POST_FAILED]}, {"next": "DONE"}],
            }
        )
        session_id = start(workspace, flow, capsys)

        code, _ = answer(workspace, session_id, capsys, *success({}, text="approved"))

        assert code == 0
        assert cast(dict, state_of(workspace, session_id)["outputs"])["RECOVER"] == "recovered"

    def test_a_resume_without_an_answer_runs_no_function_and_asks_again(self, workspace, capsys):
        flow = _workflow(
            {
                "id": "ASK",
                "action_type": "ask",
                "action_parameters": {
                    "instruction": "Decide",
                    "answer": [],
                    "function_name": "adr015_refuse_answer",
                    "function_parameters": {"code": POST_FAILED},
                },
                "transitions": [{"next": "DONE"}],
            }
        )
        session_id = start(workspace, flow, capsys)

        code, response = answer(workspace, session_id, capsys)

        assert code == 2
        assert cast(dict, cast(dict, response["data"])["question"])["node_id"] == "ASK"
        assert state_of(workspace, session_id)["errors"] == {}

    def test_a_function_that_returns_a_fresh_output_drops_the_answered_values(self, workspace, capsys):
        """The result of the function is the whole output of the node, writes included. See ADR 015 §4."""
        flow = _workflow(
            {
                "id": "ASK",
                "action_type": "ask",
                "action_parameters": {
                    "instruction": "Decide",
                    "answer": [{"name": "decision"}],
                    "function_name": "adr015_replace_output",
                    "function_parameters": {"text": "approved"},
                },
                "transitions": [{"next": "DONE"}],
            }
        )
        session_id = start(workspace, flow, capsys)

        code, _ = answer(workspace, session_id, capsys, *success({"decision": "approved"}))

        assert code == 0
        assert "decision" not in cast(dict, state_of(workspace, session_id)["params"])
