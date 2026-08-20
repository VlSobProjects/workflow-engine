"""The ADR-0083 questionnaire scenarios as one flow, driven end to end through the CLI.

This is the yardstick of `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` turned
into a run: one workflow covering `Q`, `A`, `I`, `FQ` and `STOP`, the attempt counters, the node
`validators` and the error catalogue. `S` is out — it waits for the trust decision about a
process-running function.

The flow is a release readiness review answered by an agent: an operator names the folder, the agent
inspects it and reports, asks itself follow-up questions until it has enough, and decides. What the
flow is *for*, beyond running green, is the evidence ADR 015 asks for: which of its nodes exist only
to adjust data, and where the answer had to be constrained by wording instead of by code.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main

WORKFLOW: dict[str, object] = {
    "schema_version": "1",
    "flow_id": "adr0083-release-review",
    "start_node_id": "INIT_LOG",
    "deliverables": ["handoff_table"],
    "nodes": [
        {
            # Prepares the accumulator the FQ loop appends to. Nothing is asked and nothing is
            # decided here: the node exists because a collection has to be created before it is
            # appended to.
            "id": "INIT_LOG",
            "action_type": "function",
            "action_parameters": {"function_name": "init_list_param", "function_parameters": {"param_name": "qa_log"}},
            "transitions": [{"next": "ASK_ROOT"}],
        },
        {
            # ADR-0083 `Q`: one prepared question to the operator, answered as a typed value.
            "id": "ASK_ROOT",
            "action_type": "ask",
            "action_parameters": {
                "title": "Folder to review",
                "instruction": "Name the folder that holds the release candidate.",
                "answer": [{"name": "review_root", "type": "Path", "description": "Folder to review"}],
                "errors": {"root_unavailable": "The folder cannot be reached from where you are."},
            },
            "transitions": [
                {"errors": ["root_unavailable", "answer_failed"], "fail": "review_root_missing"},
                # ADR-0083 `auto_log_stop`: the answerer walks away and the run is failed on the spot.
                {"validator": {"equals": "abort"}, "fail": "review_abandoned"},
                {"next": "CHECK_ROOT"},
            ],
        },
        {
            # Data only. The answered value is not on the bus while the ask node's own guards run, and
            # a node `validators` entry reads the output text, so checking that the folder exists
            # costs a node that surfaces the value into an output text.
            "id": "CHECK_ROOT",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "param.review_root"}},
            "transitions": [
                # The check has to be a routing transition rather than a `validators` entry: a
                # `validators` entry fails the node, and the question the answer came from is two
                # nodes back. Going back re-enters ASK_ROOT as a fresh visit, so its `max_attempts`
                # is reset every time and nothing bounds this loop but the global hard cap.
                {
                    "next": "ASK_INSPECT",
                    "validator": {"function_name": "is_output_exist_folder"},
                },
                {"next": "ASK_ROOT"},
            ],
        },
        {
            # ADR-0083 `I`: an instruction to act outside the engine and report the aggregate.
            "id": "ASK_INSPECT",
            "action_type": "ask",
            "action_parameters": {
                "title": "Inspect the release candidate",
                "instruction": (
                    "Inspect the folder named below, then answer with 'issues' as a list of short "
                    "strings and 'report_text' as one paragraph. Put nothing else in the answer text."
                ),
                # The folder can only be shown as a field of its own: a reference does not resolve
                # inside a sentence.
                "context": "param.review_root",
                "answer": [
                    {"name": "issues", "type": "list", "description": "One short string per issue found"},
                    {"name": "report_text", "description": "The report paragraph"},
                ],
            },
            "save_as": "inspect_text",
            "transitions": [{"next": "CHECK_ISSUES"}],
        },
        {
            # Data only. Routing on how many issues came back needs the answered list in an output.
            "id": "CHECK_ISSUES",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "param.issues"}},
            "transitions": [
                {
                    "next": "FQ_CHECK",
                    "validator": {
                        "function_name": "is_collection_size_at_least",
                        "function_parameters": {"collection": "param.issues", "minimum": 1},
                    },
                },
                {"next": "ASK_APPROVE"},
            ],
        },
        {
            # Data only, and the head of the FQ loop: the size check cannot live on the node that
            # appends, because a guard sees the state as it was before its own node wrote to it.
            "id": "FQ_CHECK",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "param.qa_log"}},
            "transitions": [
                {
                    "next": "ASK_APPROVE",
                    "validator": {
                        "function_name": "is_collection_size_at_least",
                        "function_parameters": {"collection": "param.qa_log", "minimum": 2},
                    },
                },
                {"next": "ASK_FOLLOWUP"},
            ],
        },
        {
            # ADR-0083 `FQ`: the agent generates its own next question and answers it.
            "id": "ASK_FOLLOWUP",
            "action_type": "ask",
            "action_parameters": {
                "title": "Follow-up question",
                "instruction": (
                    "Ask yourself the next question the issues below raise, answer it, and report the "
                    "pair as 'qa_pair' with exactly the keys 'question' and 'answer'."
                ),
                # The issue list, likewise, can only be shown as a field of its own.
                "context": "param.issues",
                "answer": [{"name": "qa_pair", "type": "dict", "description": "Keys 'question' and 'answer'"}],
                "errors": {"followup_unanswerable": "The question cannot be answered from the material at hand."},
            },
            "max_attempts": 2,
            "transitions": [
                {"errors": ["followup_unanswerable"], "next": "ASK_APPROVE", "attempts": True},
                {"errors": ["answer_failed"], "fail": "followup_failed"},
                {"next": "FQ_COLLECT"},
            ],
        },
        {
            # Data only: the ask node cannot append its own answer to a collection.
            "id": "FQ_COLLECT",
            "action_type": "function",
            "action_parameters": {
                "function_name": "append_to_param",
                "function_parameters": {"param_name": "qa_log", "value": "param.qa_pair"},
            },
            "transitions": [{"next": "FQ_CHECK"}],
        },
        {
            # ADR-0083 `A`: a branch decision with no dialogue. The decision travels in the answer
            # text, so the node's own guards route on it and 'save_as' keeps it — no surfacing node.
            "id": "ASK_APPROVE",
            "action_type": "ask",
            "action_parameters": {
                "title": "Approve the release",
                "instruction": "Answer with exactly 'approved' or 'rejected' as the answer text, and nothing else.",
                # The report can only be shown as a field of its own.
                "context": "param.report_text",
                "options": ["approved", "rejected"],
                "answer": [],
                "errors": {"review_blocked": "The decision cannot be taken."},
            },
            "save_as": "decision",
            "max_attempts": 2,
            "transitions": [
                {"next": "HANDOFF", "validator": {"equals": "approved"}},
                {"validator": {"equals": "rejected"}, "fail": "review_rejected"},
                {"errors": ["review_blocked", "answer_failed"], "fail": "review_blocked"},
                # Anything else re-asks the question, bounded by 'max_attempts'.
                {"next": "ASK_APPROVE", "attempts": True},
            ],
        },
        {
            # ADR-0083 `handoff_ref`: the collected pairs become the deliverable.
            "id": "HANDOFF",
            "action_type": "function",
            "action_parameters": {
                "function_name": "dict_list_to_pretty_table",
                "function_parameters": {
                    "artifact_name": "handoff_table",
                    "dict_param_name": "qa_log",
                    "table_format": "csv",
                },
            },
            # A `validators` entry is the right shape here and the wrong shape at CHECK_ROOT: it
            # expands to a leading failure transition, so it asserts and cannot be routed around.
            # A node that must not silently produce no handoff wants exactly that.
            "validators": [
                {"function_name": "is_output_contains_str", "function_parameters": {"substring": "pretty_table"}}
            ],
            "transitions": [
                {"errors": ["pretty_table_no_data"], "fail": "handoff_empty"},
                {"next": "FINISH"},
            ],
        },
        {
            # ADR-0083 `STOP`.
            "id": "FINISH",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "param.decision"}},
        },
    ],
}


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, str]:
    review_root = tmp_path / "candidate"
    review_root.mkdir()
    (review_root / "release_notes.md").write_text("draft", encoding="utf-8")
    config = tmp_path / "workflow_engine_config.json"
    config.write_text(
        json.dumps({"work_dir": (tmp_path / "runtime").as_posix(), "external_modules": [], "storage": {}})
    )
    workflow = tmp_path / "release_review.json"
    workflow.write_text(json.dumps(WORKFLOW))
    return {
        "config": config.as_posix(),
        "workflow": workflow.as_posix(),
        "runtime": (tmp_path / "runtime").as_posix(),
        "review_root": review_root.as_posix(),
    }


def answer(actor: str = "agent:reviewer", **fields: object) -> str:
    return json.dumps({"status": "success", "actor": actor, **fields})


def failure(code: str, message: str, actor: str = "agent:reviewer") -> str:
    return json.dumps({"status": "failure", "error_code": code, "message": message, "actor": actor})


def state_of(workspace: dict[str, str], session_id: str) -> dict[str, object]:
    path = Path(workspace["runtime"]) / "json-storage" / session_id / "state.json"
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def start(workspace: dict[str, str], capsys) -> tuple[str, dict[str, object]]:
    code, response = run_json_cli(
        ["run", "--workflow-file", workspace["workflow"], "--config", workspace["config"]], capsys
    )
    assert code == 2, response
    return cast(str, response["session_id"]), response


def resume(
    workspace: dict[str, str], session_id: str, capsys, answer_json: str | None = None
) -> tuple[int, dict[str, object]]:
    argv = ["resume", "--session-id", session_id, "--config", workspace["config"]]
    if answer_json is not None:
        argv += ["--answer", answer_json]
    return run_json_cli(argv, capsys)


def question_of(response: dict[str, object]) -> dict[str, object]:
    data = cast(dict[str, object], response["data"])
    return cast(dict[str, object], data["question"])


def qa(index: int) -> str:
    return answer(values={"qa_pair": {"question": f"question {index}", "answer": f"answer {index}"}})


def param_value(state: dict[str, object], name: str) -> object:
    """The stored value of a state parameter, unwrapped from its codec envelope."""
    params = cast(dict[str, object], state["params"])
    stored = cast(dict[str, object], params[name])["value"]
    if isinstance(stored, dict) and "object" in stored:
        return stored["object"]
    return stored


def test_the_flow_runs_through_every_adr0083_node_type(workspace, capsys):
    """Q, I, FQ twice, A, the handoff deliverable and STOP, in one pass."""
    session_id, response = start(workspace, capsys)
    assert question_of(response)["node_id"] == "ASK_ROOT"

    code, response = resume(workspace, session_id, capsys, answer(values={"review_root": workspace["review_root"]}))
    assert code == 2, response
    question = question_of(response)
    assert question["node_id"] == "ASK_INSPECT"
    # The folder reaches the agent as a field of its own, not inside the instruction.
    assert question["context"] == workspace["review_root"]

    code, response = resume(
        workspace,
        session_id,
        capsys,
        answer(
            values={"issues": ["no changelog entry", "version not bumped"], "report_text": "Two issues found."},
            text="reported",
        ),
    )
    assert code == 2, response
    assert question_of(response)["node_id"] == "ASK_FOLLOWUP"

    for index in (1, 2):
        code, response = resume(workspace, session_id, capsys, qa(index))
        assert code == 2, response

    question = question_of(response)
    assert question["node_id"] == "ASK_APPROVE"
    assert question["context"] == "Two issues found."
    assert question["answer"] == []

    code, response = resume(workspace, session_id, capsys, answer(text="approved"))
    assert code == 0, response

    state = state_of(workspace, session_id)
    assert param_value(state, "decision") == "approved"
    assert param_value(state, "inspect_text") == "reported"
    assert len(cast(list[object], param_value(state, "qa_log"))) == 2
    assert "handoff_table" in cast(dict[str, object], state["artifacts"])


def test_a_decision_the_wording_did_not_constrain_re_asks_until_the_attempts_run_out(workspace, capsys):
    """`max_attempts` is the only thing standing between a wrong word and a wrong route."""
    session_id, _ = start(workspace, capsys)
    resume(workspace, session_id, capsys, answer(values={"review_root": workspace["review_root"]}))
    resume(workspace, session_id, capsys, answer(values={"issues": [], "report_text": "Nothing found."}))
    # No issues, so the FQ loop is skipped and the decision is asked directly.
    for text in ("Looks good to me!", "LGTM"):
        code, response = resume(workspace, session_id, capsys, answer(text=text))
        assert code == 2, response
        assert question_of(response)["node_id"] == "ASK_APPROVE"

    code, response = resume(workspace, session_id, capsys, answer(text="approve"))
    assert code == 3, response
    assert "max_attempts_exceeded" in json.dumps(response)


def test_a_rejected_release_fails_the_run_under_its_own_code(workspace, capsys):
    session_id, _ = start(workspace, capsys)
    resume(workspace, session_id, capsys, answer(values={"review_root": workspace["review_root"]}))
    resume(workspace, session_id, capsys, answer(values={"issues": [], "report_text": "Nothing found."}))
    code, response = resume(workspace, session_id, capsys, answer(text="rejected"))
    assert code == 3, response
    assert "review_rejected" in json.dumps(response)


def test_an_answer_whose_node_then_fails_is_journaled_and_its_values_are_applied(workspace, capsys):
    """The precedent ADR 015 open point 4 needs: this already happens, and the values do land.

    The engine applies a node's writes before it looks at whether the step failed, so a success answer
    that routes straight into a `fail` target leaves both an `interactive_answered` event and the
    values it carried on the bus. What it does not leave is `save_as`, which is skipped once the output
    carries an error code.
    """
    session_id, _ = start(workspace, capsys)
    code, response = resume(
        workspace, session_id, capsys, answer(values={"review_root": workspace["review_root"]}, text="abort")
    )
    assert code == 3, response
    assert "review_abandoned" in json.dumps(response)

    state = state_of(workspace, session_id)
    answered = [event for event in cast(list[dict], state["session_events"]) if event["code"] == "interactive_answered"]
    assert [event["details"]["names"] for event in answered] == [["review_root"]]
    assert param_value(state, "review_root") == workspace["review_root"]


def test_a_failure_answer_routes_on_its_declared_code(workspace, capsys):
    session_id, response = start(workspace, capsys)
    assert question_of(response)["error_catalogue"] == {
        "root_unavailable": "The folder cannot be reached from where you are."
    }
    code, response = resume(
        workspace, session_id, capsys, failure("root_unavailable", "No such folder here.", actor="operator:release")
    )
    assert code == 3, response
    assert "review_root_missing" in json.dumps(response)


def test_a_bad_answer_is_caught_one_node_later_and_the_retry_is_unbounded(workspace, capsys):
    """The answered value is checked one node later, because the ask node's guards cannot see it.

    The consequence is the point: the retry re-enters the question as a fresh visit, so the node's own
    `max_attempts` never counts up. The same wrong answer can be given forever, and only the global
    hard cap of ADR 010 stands in the way.
    """
    session_id, _ = start(workspace, capsys)
    for _ in range(5):
        code, response = resume(
            workspace, session_id, capsys, answer(values={"review_root": workspace["review_root"] + "/missing"})
        )
        assert code == 2, response
        assert question_of(response)["node_id"] == "ASK_ROOT"

    state = state_of(workspace, session_id)
    assert cast(dict[str, object], state["attempt_counters"])["ASK_ROOT"] == 0
    assert cast(dict[str, object], state["visit_counters"])["ASK_ROOT"] == 5
