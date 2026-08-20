"""The ADR-0083 questionnaire scenarios as one flow, driven end to end through the CLI.

This is the yardstick of `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` turned
into a run: one workflow covering `Q`, `A`, `I`, `FQ` and `STOP`, the attempt counters, the node
`validators` and the error catalogue. `S` is out — it waits for the trust decision about a
process-running function.

The flow is a release readiness review answered by an agent: an operator names the folder, the agent
inspects it and reports, asks itself follow-up questions until it has enough, and decides. It was
written as eleven nodes, four of which existed only to adjust data beside a question; with the post
function pair of ADR 015 in the core those four are folded into the questions they served and seven
are left, each of which asks, produces or stops. What the flow is *for*, beyond running green, is
that measurement and the one it did not answer: where an answer still has to be constrained by
wording instead of by code.
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
            # The question checks what it bound: 'echo_answer' puts the answered folder into the
            # output text before the transitions are selected, so the check that used to cost the
            # CHECK_ROOT node is a guard on this node's own routing (ADR 015).
            "id": "ASK_ROOT",
            "action_type": "ask",
            "action_parameters": {
                "title": "Folder to review",
                "instruction": "Name the folder that holds the release candidate.",
                "answer": [{"name": "review_root", "type": "Path", "description": "Folder to review"}],
                "errors": {
                    "root_unavailable": "The folder cannot be reached from where you are.",
                    # ADR-0083 `auto_log_stop`: the answerer walks away. With the check folded in,
                    # the node routes on the folder rather than on the answer text, so walking away
                    # is the declared refusal the contract always had, not a word in the text.
                    "review_abandoned": "The review is abandoned; no folder will be named.",
                },
                "function_name": "echo_answer",
                "function_parameters": {"name": "review_root"},
            },
            # A rejected folder now re-asks in place, so the bound is the node's own attempts. The
            # visit cap that used to save this loop is not needed: nothing leaves and comes back.
            "max_attempts": 2,
            "transitions": [
                {"errors": ["root_unavailable", "answer_failed"], "fail": "review_root_missing"},
                {"errors": ["review_abandoned"], "fail": "review_abandoned"},
                {"next": "ASK_INSPECT", "validator": {"function_name": "is_output_exist_folder"}},
                {"next": "ASK_ROOT"},
            ],
        },
        {
            # ADR-0083 `I`: an instruction to act outside the engine and report the aggregate.
            # The answered issue list is surfaced by the node itself, so the branch on "anything to
            # follow up?" is taken here instead of in a CHECK_ISSUES node behind it.
            "id": "ASK_INSPECT",
            "action_type": "ask",
            "action_parameters": {
                "title": "Inspect the release candidate",
                "instruction": (
                    "Inspect the folder '${param.review_root}', then answer with 'issues' as a list "
                    "of short strings and 'report_text' as one paragraph. Put nothing else in the "
                    "answer text."
                ),
                "answer": [
                    {"name": "issues", "type": "list", "description": "One short string per issue found"},
                    {"name": "report_text", "description": "The report paragraph"},
                ],
                "function_name": "echo_answer",
                "function_parameters": {"name": "issues"},
            },
            # With a post function configured, 'save_as' keeps what the function returned rather than
            # what was answered: the surfaced issue list, not the answer text (ADR 015).
            "save_as": "inspect_text",
            "transitions": [
                # A surfaced collection is compact JSON (ADR 016), so an empty issue list is
                # literally '[]'. Counting it is not expressible here: 'is_collection_size_at_least'
                # resolves its collection from the state, where an answered value has not landed yet.
                {"next": "ASK_APPROVE", "validator": {"equals": "[]"}},
                {"next": "ASK_FOLLOWUP"},
            ],
        },
        {
            # ADR-0083 `FQ`: the agent generates its own next question and answers it. One node:
            # 'collect_answer' appends the pair and reports whether the loop has enough, which is
            # what the FQ_CHECK head and the FQ_COLLECT tail used to do between them.
            "id": "ASK_FOLLOWUP",
            "action_type": "ask",
            "action_parameters": {
                "title": "Follow-up question",
                # The issue list is a collection, so ADR 016 renders it into the sentence as compact
                # JSON rather than as the Python repr a bare field used to carry.
                "instruction": (
                    "Ask yourself the next question these issues raise: ${param.issues}. Answer it, "
                    "and report the pair as 'qa_pair' with exactly the keys 'question' and 'answer'."
                ),
                "answer": [{"name": "qa_pair", "type": "dict", "description": "Keys 'question' and 'answer'"}],
                "errors": {"followup_unanswerable": "The question cannot be answered from the material at hand."},
                "function_name": "collect_answer",
                "function_parameters": {"param_name": "qa_log", "minimum": 2, "name": "qa_pair"},
            },
            # The loop now runs in place, so it spends the attempts the node declares: two collected
            # pairs are one attempt, and what is left bounds the unanswerable retry below.
            "max_attempts": 3,
            "transitions": [
                {"errors": ["followup_unanswerable"], "next": "ASK_APPROVE", "attempts": True},
                {"errors": ["answer_failed"], "fail": "followup_failed"},
                {"next": "ASK_APPROVE", "validator": {"equals": "enough"}},
                {"next": "ASK_FOLLOWUP"},
            ],
        },
        {
            # ADR-0083 `A`: a branch decision with no dialogue. The decision travels in the answer
            # text, so the node's own guards route on it and 'save_as' keeps it — and no post
            # function belongs here, because one would replace the very text the guards compare.
            "id": "ASK_APPROVE",
            "action_type": "ask",
            "action_parameters": {
                "title": "Approve the release",
                "instruction": (
                    "The review reported: ${param.report_text}. Answer with exactly 'approved' or "
                    "'rejected' as the answer text, and nothing else."
                ),
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
            # A `validators` entry asserts and cannot be routed around: it expands to a leading
            # failure transition. A node that must not silently produce no handoff wants exactly that.
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


def test_the_flow_is_the_seven_nodes_the_coverage_note_predicted():
    """Eleven nodes minus the four that only adjusted data beside a question. See the note, item 5."""
    node_ids = [cast(dict, node)["id"] for node in cast(list[object], WORKFLOW["nodes"])]

    assert node_ids == ["INIT_LOG", "ASK_ROOT", "ASK_INSPECT", "ASK_FOLLOWUP", "ASK_APPROVE", "HANDOFF", "FINISH"]


def test_the_flow_runs_through_every_adr0083_node_type(workspace, capsys):
    """Q, I, FQ twice, A, the handoff deliverable and STOP, in one pass."""
    session_id, response = start(workspace, capsys)
    assert question_of(response)["node_id"] == "ASK_ROOT"

    code, response = resume(workspace, session_id, capsys, answer(values={"review_root": workspace["review_root"]}))
    assert code == 2, response
    question = question_of(response)
    assert question["node_id"] == "ASK_INSPECT"
    # The folder reaches the agent inside the sentence that tells it what to do (ADR 016).
    assert workspace["review_root"] in cast(str, question["instruction"])
    assert "context" not in question

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

    # The issue list stands inside the follow-up question as compact JSON, not as a Python repr.
    assert '["no changelog entry","version not bumped"]' in cast(str, question_of(response)["instruction"])

    for index in (1, 2):
        code, response = resume(workspace, session_id, capsys, qa(index))
        assert code == 2, response

    question = question_of(response)
    assert question["node_id"] == "ASK_APPROVE"
    assert "Two issues found." in cast(str, question["instruction"])
    assert question["answer"] == []

    code, response = resume(workspace, session_id, capsys, answer(text="approved"))
    assert code == 0, response

    state = state_of(workspace, session_id)
    assert param_value(state, "decision") == "approved"
    # The node asked and computed, so what it produced is the surfaced issue list, not "reported".
    assert param_value(state, "inspect_text") == '["no changelog entry","version not bumped"]'
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


@pytest.mark.parametrize(
    ("declared_code", "failure_code"),
    [("root_unavailable", "review_root_missing"), ("review_abandoned", "review_abandoned")],
)
def test_a_failure_answer_routes_on_its_declared_code(workspace, capsys, declared_code, failure_code):
    """Both refusals the first question declares, including the answerer who walks away.

    Walking away is a failure answer rather than a word in the answer text: the question now computes
    on what it bound, so its own guards compare the folder that was named and no longer the text that
    came with it. ADR-0083 `auto_log_stop` is the `FailTarget` this routes into, plus the
    `interactive_answered` event the refusal leaves behind.
    """
    session_id, response = start(workspace, capsys)
    assert question_of(response)["error_catalogue"] == {
        "root_unavailable": "The folder cannot be reached from where you are.",
        "review_abandoned": "The review is abandoned; no folder will be named.",
    }
    code, response = resume(
        workspace, session_id, capsys, failure(declared_code, "Not going further.", actor="operator:release")
    )
    assert code == 3, response
    assert failure_code in json.dumps(response)


def test_the_question_checks_what_it_bound_and_its_own_attempts_bound_the_retry(workspace, capsys):
    """What used to cost a node behind the question, and an unbounded retry, is one node again.

    The check that catches an unreachable folder is a guard on this node's own routing, because the
    post function surfaces the answered value before the transitions are selected (ADR 015). The
    correction therefore re-asks in place, which is an *attempt*, so `max_attempts` bounds it at the
    question itself — the `max_visits` seatbelt of ADR 017 is not what saves this run any more, and
    the node no longer declares one.

    It also carries the precedent ADR 015 open point 4 needed: the answers were accepted, so their
    values are on the bus and the journal records them, even though the node they belong to failed.
    """
    session_id, _ = start(workspace, capsys)
    missing = workspace["review_root"] + "/missing"
    for _ in range(2):
        code, response = resume(workspace, session_id, capsys, answer(values={"review_root": missing}))
        assert code == 2, response
        assert question_of(response)["node_id"] == "ASK_ROOT"

    code, response = resume(workspace, session_id, capsys, answer(values={"review_root": missing}))
    assert code == 3, response
    assert "max_attempts_exceeded" in json.dumps(response)

    state = state_of(workspace, session_id)
    # One visit: the correction never left the node, which is why the attempts are what ran out.
    assert cast(dict[str, object], state["visit_counters"])["ASK_ROOT"] == 1
    answered = [event for event in cast(list[dict], state["session_events"]) if event["code"] == "interactive_answered"]
    assert [event["details"]["names"] for event in answered] == [["review_root"]] * 3
    assert param_value(state, "review_root") == missing
