"""A loop that collects answers and leaves once it has enough, end to end through the CLI.

This is the shape the external ADR-0083 `FQ` node needs — up to N agent-generated questions, each
answer kept — and the reason `append_to_param` and `is_collection_size_at_least` exist. The engine can
bound the *retries* of a node with `attempts`, but a loop that passes through a second node resets that
counter, so the bound has to come from what the loop has collected. See
`docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main

WORKFLOW = {
    "schema_version": "1",
    "flow_id": "bounded-accumulating-loop",
    "start_node_id": "INIT",
    "nodes": [
        {
            "id": "INIT",
            "action_type": "function",
            "action_parameters": {"function_name": "init_list_param", "function_parameters": {"param_name": "answers"}},
            "transitions": [{"next": "CHECK"}],
        },
        {
            # The head of the loop. The check lives here and not on COLLECT because a guard runs before
            # the writes of its own node are applied: at COLLECT the append has not landed yet.
            "id": "CHECK",
            "action_type": "function",
            "action_parameters": {
                "function_name": "echo_value",
                "function_parameters": {"value": "param.answers"},
            },
            "transitions": [
                {
                    "next": "REPORT",
                    "validator": {
                        "function_name": "is_collection_size_at_least",
                        "function_parameters": {"collection": "param.answers", "minimum": 3},
                    },
                },
                {"next": "ASK"},
            ],
        },
        {
            "id": "ASK",
            "action_type": "ask",
            "action_parameters": {
                "title": "Next question",
                "instruction": "Ask the operator your next question and report the answer.",
                "answer": [{"name": "last_answer", "description": "The answer you obtained"}],
            },
            "transitions": [{"next": "COLLECT"}],
        },
        {
            "id": "COLLECT",
            "action_type": "function",
            "action_parameters": {
                "function_name": "append_to_param",
                "function_parameters": {"param_name": "answers", "value": "param.last_answer"},
            },
            "transitions": [{"next": "CHECK"}],
        },
        {
            "id": "REPORT",
            "action_type": "stop",
            "action_parameters": {
                "function_name": "echo_value",
                "function_parameters": {"value": "param.answers"},
            },
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
    workflow = tmp_path / "loop.json"
    workflow.write_text(json.dumps(WORKFLOW))
    return {
        "config": config.as_posix(),
        "workflow": workflow.as_posix(),
        "runtime": (tmp_path / "runtime").as_posix(),
    }


def answer(text: str) -> str:
    return json.dumps({"status": "success", "values": {"last_answer": text}, "actor": "agent:asker"})


def state_of(workspace: dict[str, str], session_id: str) -> dict[str, object]:
    path = Path(workspace["runtime"]) / "json-storage" / session_id / "state.json"
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_the_loop_collects_three_answers_and_then_leaves(workspace, capsys):
    code, response = run_json_cli(
        ["run", "--workflow-file", workspace["workflow"], "--config", workspace["config"]], capsys
    )
    assert code == 2
    session_id = cast(str, response["session_id"])

    for text in ("first", "second"):
        code, response = run_json_cli(
            ["resume", "--session-id", session_id, "--config", workspace["config"], "--answer", answer(text)], capsys
        )
        assert code == 2, "the loop must come back to the question until it has enough"
        assert cast(dict, cast(dict, response["data"])["question"])["node_id"] == "ASK"

    code, response = run_json_cli(
        ["resume", "--session-id", session_id, "--config", workspace["config"], "--answer", answer("third")], capsys
    )

    assert code == 0
    assert response["workflow_status"] == "completed"
    state = state_of(workspace, session_id)
    # A list parameter persists each item through its own codec, so the stored form is a list of
    # encoded values rather than a list of strings.
    stored = cast(list, cast(dict, cast(dict, cast(dict, state["params"])["answers"])["value"])["object"])
    assert [cast(dict, item)["object"] for item in stored] == ["first", "second", "third"]
    assert cast(dict, state["outputs"])["REPORT"] == "['first', 'second', 'third']"


def test_every_pass_is_counted_as_a_visit_and_no_attempt_is_consumed(workspace, capsys):
    _, response = run_json_cli(
        ["run", "--workflow-file", workspace["workflow"], "--config", workspace["config"]], capsys
    )
    session_id = cast(str, response["session_id"])
    for text in ("first", "second", "third"):
        run_json_cli(
            ["resume", "--session-id", session_id, "--config", workspace["config"], "--answer", answer(text)], capsys
        )

    state = state_of(workspace, session_id)
    # The loop leaves the node every pass, so it counts visits and never touches `max_attempts`.
    assert cast(dict, state["visit_counters"])["ASK"] == 3
    assert cast(dict, state["attempt_counters"])["ASK"] == 0
