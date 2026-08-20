"""ADR 013 end to end: the `examples/approve-and-copy.json` exchange driven through the CLI.

The template pauses at an `ask` node, so every path here needs two commands at least: the `run` that
stops at the question and the `resume` that answers it. The refusal paths assert that a refused
command changed nothing at all, which is the part of the contract a caller has to be able to rely on.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.answers import ANSWER_FAILED
from workflow_engine.cli.main import main
from workflow_engine.models.state import SessionEventCode

TEMPLATE = Path(__file__).resolve().parents[1] / "examples" / "approve-and-copy.json"


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, str]:
    config_path = tmp_path / "workflow_engine_config.json"
    config_path.write_text(
        json.dumps({"work_dir": (tmp_path / "runtime").as_posix(), "external_modules": [], "storage": {}})
    )
    source = tmp_path / "source.txt"
    source.write_text("content to copy")
    target = tmp_path / "out"
    target.mkdir()
    return {
        "config": config_path.as_posix(),
        "source": source.as_posix(),
        "target": target.as_posix(),
        "runtime": (tmp_path / "runtime").as_posix(),
    }


def start(workspace: dict[str, str], capsys) -> tuple[str, dict[str, object]]:
    code, response = run_json_cli(
        [
            "run",
            "--workflow-file",
            TEMPLATE.as_posix(),
            "--config",
            workspace["config"],
            "--input",
            f"source_file:Path={workspace['source']}",
            "--input",
            f"target_dir:Path={workspace['target']}",
        ],
        capsys,
    )
    assert code == 2
    return cast(str, response["session_id"]), response


def resume(workspace: dict[str, str], session_id: str, capsys, *answer: str) -> tuple[int, dict[str, object]]:
    return run_json_cli(["resume", "--session-id", session_id, "--config", workspace["config"], *answer], capsys)


def state_of(workspace: dict[str, str], session_id: str) -> dict[str, object]:
    path = Path(workspace["runtime"]) / "json-storage" / session_id / "state.json"
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def event_codes(state: dict[str, object]) -> list[str]:
    return [cast(dict, event)["code"] for event in cast(list, state["session_events"])]


class TestPausing:
    def test_the_run_stops_at_the_question_and_publishes_it(self, workspace, capsys):
        _, response = start(workspace, capsys)
        assert response["workflow_status"] == "paused"
        assert response["event_code"] == SessionEventCode.WORKFLOW_PAUSED_INTERACTIVE.value
        question = cast(dict, cast(dict, response["data"])["question"])
        assert question["node_id"] == "ASK_APPROVAL"
        assert [entry["name"] for entry in cast(list, question["answer"])] == ["reviewer"]
        assert question["error_catalogue"] == {
            "source_unreadable": "The file cannot be read, so no decision can be made."
        }
        assert question["generic_error_code"] == ANSWER_FAILED
        # The file and its size stand inside the instruction, not beside it (ADR 016).
        assert workspace["source"] in cast(str, question["instruction"])
        assert "context" not in question and "hints" not in question
        assert response["errors"] == {}

    def test_the_pause_is_journaled_with_the_declared_names(self, workspace, capsys):
        session_id, _ = start(workspace, capsys)
        last = cast(list, state_of(workspace, session_id)["session_events"])[-1]
        assert last["code"] == SessionEventCode.WORKFLOW_PAUSED_INTERACTIVE.value
        assert last["actor"] == "engine"
        assert last["details"] == {"node_id": "ASK_APPROVAL", "answer": ["reviewer"]}


class TestAnswering:
    def test_a_success_answer_binds_its_values_and_routes_the_run(self, workspace, capsys):
        session_id, _ = start(workspace, capsys)
        code, response = resume(
            workspace,
            session_id,
            capsys,
            "--answer",
            json.dumps(
                {
                    "status": "success",
                    "values": {"reviewer": "vlad"},
                    "text": "approved",
                    "actor": "agent:reviewer-bot",
                }
            ),
        )
        assert code == 0
        assert response["workflow_status"] == "completed"
        assert "question" not in cast(dict, response["data"])
        assert (Path(workspace["target"]) / "source.txt").read_text() == "content to copy"

        state = state_of(workspace, session_id)
        reviewer = cast(dict, cast(dict, state["params"])["reviewer"])
        assert cast(dict, reviewer["value"])["object"] == "vlad"
        assert reviewer["source_node_id"] == "ASK_APPROVAL"
        assert cast(dict, state["outputs"])["ASK_APPROVAL"] == "approved"

    def test_the_answer_is_journaled_without_its_values(self, workspace, capsys):
        session_id, _ = start(workspace, capsys)
        resume(
            workspace,
            session_id,
            capsys,
            "--answer",
            json.dumps({"status": "success", "values": {"reviewer": "vlad"}, "text": "approved", "actor": "operator"}),
        )
        answered = next(
            event
            for event in cast(list, state_of(workspace, session_id)["session_events"])
            if cast(dict, event)["code"] == SessionEventCode.INTERACTIVE_ANSWERED.value
        )
        assert answered["actor"] == "operator"
        assert answered["details"] == {
            "node_id": "ASK_APPROVAL",
            "visit": 1,
            "attempt": 1,
            "status": "success",
            "actor": "operator",
            "names": ["reviewer"],
            "codecs": {"reviewer": None},
        }

    def test_the_file_transport_answers_the_same_way(self, workspace, capsys, tmp_path):
        session_id, _ = start(workspace, capsys)
        answer_file = tmp_path / "answer.json"
        answer_file.write_text(
            json.dumps({"status": "success", "values": {"reviewer": "vlad"}, "text": "approved"}), encoding="utf-8"
        )
        code, response = resume(workspace, session_id, capsys, "--answer-file", answer_file.as_posix())
        assert code == 0
        assert response["workflow_status"] == "completed"

    def test_a_failure_answer_routes_on_its_error_code(self, workspace, capsys):
        session_id, _ = start(workspace, capsys)
        code, response = resume(
            workspace,
            session_id,
            capsys,
            "--answer",
            json.dumps({"status": "failure", "error_code": "source_unreadable", "message": "no access"}),
        )
        assert code == 3
        assert response["workflow_status"] == "failed"
        assert cast(dict, response["data"])["error_code"] == "approval_failed"

    def test_an_unrecognized_answer_text_asks_again_until_the_attempts_run_out(self, workspace, capsys):
        session_id, _ = start(workspace, capsys)
        undecided = json.dumps({"status": "success", "values": {"reviewer": "vlad"}, "text": "maybe"})
        for _ in range(2):
            code, response = resume(workspace, session_id, capsys, "--answer", undecided)
            assert code == 2
            assert cast(dict, cast(dict, response["data"])["question"])["node_id"] == "ASK_APPROVAL"
        code, response = resume(workspace, session_id, capsys, "--answer", undecided)
        assert code == 3
        assert cast(dict, response["data"])["error_code"] == "max_attempts_exceeded"


class TestRePresenting:
    def test_a_resume_without_an_answer_asks_the_same_question_again(self, workspace, capsys):
        session_id, first = start(workspace, capsys)
        code, second = resume(workspace, session_id, capsys)
        assert code == 2
        assert cast(dict, second["data"])["question"] == cast(dict, first["data"])["question"]

    def test_it_consumes_neither_an_attempt_nor_a_visit(self, workspace, capsys):
        session_id, _ = start(workspace, capsys)
        before = state_of(workspace, session_id)
        resume(workspace, session_id, capsys)
        after = state_of(workspace, session_id)
        assert after["nodes_visited"] == before["nodes_visited"]
        assert after["attempt_counters"] == before["attempt_counters"]
        assert after["visit_counters"] == before["visit_counters"]


class TestRefusals:
    @pytest.mark.parametrize(
        "answer",
        [
            '{"status": "success", "values": {"undeclared": "x"}}',
            '{"status": "success"}',
            '{"status": "failure", "error_code": "invented"}',
            '{"status": "escalate"}',
            "not json at all",
        ],
    )
    def test_a_refused_answer_exits_four_and_changes_nothing(self, workspace, capsys, answer):
        session_id, _ = start(workspace, capsys)
        before = state_of(workspace, session_id)

        code, response = resume(workspace, session_id, capsys, "--answer", answer)

        assert code == 4
        assert response["command_status"] == "error"
        assert state_of(workspace, session_id) == before

    def test_an_answer_to_a_run_that_asked_nothing_is_refused(self, workspace, capsys):
        session_id, _ = start(workspace, capsys)
        resume(
            workspace,
            session_id,
            capsys,
            "--answer",
            json.dumps({"status": "success", "values": {"reviewer": "vlad"}, "text": "approved"}),
        )
        before = state_of(workspace, session_id)
        assert event_codes(before)[-1] == SessionEventCode.WORKFLOW_COMPLETED.value

        code, _ = resume(
            workspace,
            session_id,
            capsys,
            "--answer",
            json.dumps({"status": "success", "values": {"reviewer": "again"}}),
        )
        assert code == 4
        assert state_of(workspace, session_id) == before

    def test_both_transports_at_once_are_a_command_line_error(self, workspace, capsys, tmp_path):
        session_id, _ = start(workspace, capsys)
        code, response = resume(
            workspace, session_id, capsys, "--answer", "{}", "--answer-file", (tmp_path / "a.json").as_posix()
        )
        assert code == 4
        assert response["command_status"] == "error"
