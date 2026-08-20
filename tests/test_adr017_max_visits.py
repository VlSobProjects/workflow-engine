"""The per-node visit cap, end to end through the CLI. See ADR 017.

`max_attempts` bounds the retries of one visit and the ADR 010 caps bound the whole run; between them
a loop through two nodes was bounded by nothing, because leaving a node resets its attempt counter.
`max_visits` is the declared ceiling that closes the gap: the engine checks it when it is about to run
the node, so a question beyond the cap is never asked and the run stops at the node that caused it.
"""

import copy
import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main

AUTOMATIC_LOOP = {
    "schema_version": "1",
    "flow_id": "automatic-visit-loop",
    "start_node_id": "LOOP",
    "nodes": [
        {
            # A loop through two nodes: every pass leaves the node, so it counts a visit and never
            # touches `max_attempts`. Nothing in the flow itself ever ends it.
            "id": "LOOP",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "tick"}},
            "max_visits": 3,
            "transitions": [{"next": "TURN"}],
        },
        {
            "id": "TURN",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "turn"}},
            "transitions": [{"next": "LOOP"}],
        },
    ],
}

INTERACTIVE_LOOP = {
    "schema_version": "1",
    "flow_id": "interactive-visit-loop",
    "start_node_id": "ASK",
    "nodes": [
        {
            # Three routes out of one question: the answer that ends the run, the answer that leaves
            # the node and comes back through another node - a visit - and everything else, which
            # re-asks in place and consumes an attempt.
            "id": "ASK",
            "action_type": "ask",
            "action_parameters": {
                "title": "Say the word",
                "instruction": (
                    "Answer with 'ok' to finish, 'elsewhere' to be sent around, anything else to be asked again."
                ),
                "answer": [],
            },
            "max_attempts": 5,
            "max_visits": 3,
            "transitions": [
                {"next": "DONE", "validator": {"equals": "ok"}},
                {"next": "TURN", "validator": {"equals": "elsewhere"}},
                {"next": "ASK", "attempts": True},
            ],
        },
        {
            "id": "TURN",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "turn"}},
            "transitions": [{"next": "ASK"}],
        },
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        },
    ],
}


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def build_workspace(tmp_path: Path, workflow: dict[str, object]) -> dict[str, str]:
    config = tmp_path / "workflow_engine_config.json"
    config.write_text(
        json.dumps({"work_dir": (tmp_path / "runtime").as_posix(), "external_modules": [], "storage": {}})
    )
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(json.dumps(workflow))
    return {
        "config": config.as_posix(),
        "workflow": workflow_file.as_posix(),
        "runtime": (tmp_path / "runtime").as_posix(),
    }


def without_key(workflow: dict[str, object], node_id: str, key: str) -> dict[str, object]:
    stripped = copy.deepcopy(workflow)
    for node in cast(list[dict[str, object]], stripped["nodes"]):
        if node["id"] == node_id:
            node.pop(key)
    return stripped


def with_value(workflow: dict[str, object], node_id: str, key: str, value: object) -> dict[str, object]:
    changed = copy.deepcopy(workflow)
    for node in cast(list[dict[str, object]], changed["nodes"]):
        if node["id"] == node_id:
            node[key] = value
    return changed


def state_of(workspace: dict[str, str], session_id: str) -> dict[str, object]:
    path = Path(workspace["runtime"]) / "json-storage" / session_id / "state.json"
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def answer(text: str) -> str:
    return json.dumps({"status": "success", "values": {}, "text": text, "actor": "agent:tester"})


def resume(workspace: dict[str, str], session_id: str, capsys, *extra: str) -> tuple[int, dict[str, object]]:
    return run_json_cli(
        ["resume", "--session-id", session_id, "--config", workspace["config"], *extra],
        capsys,
    )


def start(workspace: dict[str, str], capsys) -> tuple[int, dict[str, object]]:
    return run_json_cli(
        ["run", "--workflow-file", workspace["workflow"], "--config", workspace["config"]],
        capsys,
    )


def answered_ordinals(state: dict[str, object]) -> list[tuple[object, object]]:
    return [
        (cast(dict, event)["details"]["visit"], cast(dict, event)["details"]["attempt"])
        for event in cast(list, state["session_events"])
        if cast(dict, event)["code"] == "interactive_answered"
    ]


class TestAutomaticLoop:
    def test_the_node_runs_the_visits_it_declares_and_the_next_entry_fails_the_run(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, AUTOMATIC_LOOP)
        code, response = start(workspace, capsys)

        assert code == 3, response
        assert response["workflow_status"] == "failed"
        assert response["event_code"] == "workflow_failed"
        assert cast(dict, response["data"])["error_code"] == "max_visits_exceeded"
        # Three completed visits and no fourth: the cap is checked before the action, so the node is
        # entered exactly as many times as it declares.
        state = state_of(workspace, session_id_of(response))
        assert cast(dict, state["visit_counters"])["LOOP"] == 3
        assert cast(dict, state["visit_counters"])["TURN"] == 3

    def test_without_the_key_nothing_per_node_bounds_the_same_loop(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, without_key(AUTOMATIC_LOOP, "LOOP", "max_visits"))
        _, response = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                workspace["workflow"],
                "--max-nodes-visited",
                "9",
                "--config",
                workspace["config"],
            ],
            capsys,
        )
        session_id = session_id_of(response)
        code, response = resume(workspace, session_id, capsys)

        # The run is stopped by the ADR 010 session budget, not by the node, and it is stopped well
        # past the three visits the declared cap allowed above.
        assert code == 2, response
        assert response["event_code"] == "workflow_paused_limit"
        assert cast(dict, state_of(workspace, session_id)["visit_counters"])["LOOP"] > 3

    def test_the_capped_node_cannot_route_its_own_exhaustion(self, tmp_path, capsys):
        routed = with_value(
            AUTOMATIC_LOOP,
            "LOOP",
            "transitions",
            [{"errors": ["max_visits_exceeded"], "next": "TURN"}, {"next": "TURN"}],
        )
        workspace = build_workspace(tmp_path, routed)
        code, response = start(workspace, capsys)

        # The check precedes the action, so there is no output for the node's own transitions to see.
        # The declared route is simply never consulted and the workflow fails. See ADR 017 §3.
        assert code == 3, response
        assert cast(dict, response["data"])["error_code"] == "max_visits_exceeded"

    def test_a_declared_cap_below_one_is_refused_as_a_configuration_error(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, with_value(AUTOMATIC_LOOP, "LOOP", "max_visits", 0))
        code, response = start(workspace, capsys)

        assert code == 4, response
        assert response["command_status"] == "error"
        assert "max_visits" in json.dumps(response)


class TestInteractiveLoop:
    def test_a_question_beyond_the_cap_is_never_asked(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, with_value(INTERACTIVE_LOOP, "ASK", "max_visits", 2))
        code, response = start(workspace, capsys)
        assert code == 2, response
        session_id = session_id_of(response)

        code, response = resume(workspace, session_id, capsys, "--answer", answer("elsewhere"))
        assert code == 2, "one visit is spent, the second is still allowed"
        assert cast(dict, cast(dict, response["data"])["question"])["node_id"] == "ASK"

        code, response = resume(workspace, session_id, capsys, "--answer", answer("elsewhere"))

        # The spend stops before it happens: the run fails on the way into the question rather than
        # publishing a third one and waiting to be paid for it.
        assert code == 3, response
        assert cast(dict, response["data"])["error_code"] == "max_visits_exceeded"
        assert "question" not in cast(dict, response["data"])
        assert cast(dict, state_of(workspace, session_id)["visit_counters"])["ASK"] == 2

    def test_re_presenting_a_question_consumes_no_visit_and_does_not_move_the_cap(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, with_value(INTERACTIVE_LOOP, "ASK", "max_visits", 1))
        _, response = start(workspace, capsys)
        session_id = session_id_of(response)

        # ADR 013 §6: a plain resume hands the question on and consumes nothing. The node is on its
        # only allowed visit, and asking again may not end it.
        for _ in range(3):
            code, response = resume(workspace, session_id, capsys)
            assert code == 2, response
            assert cast(dict, cast(dict, response["data"])["question"])["node_id"] == "ASK"

        assert "ASK" not in cast(dict, state_of(workspace, session_id)["visit_counters"])

        code, response = resume(workspace, session_id, capsys, "--answer", answer("ok"))
        assert code == 0, response

    def test_an_attempt_in_place_does_not_consume_a_visit(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, with_value(INTERACTIVE_LOOP, "ASK", "max_visits", 1))
        _, response = start(workspace, capsys)
        session_id = session_id_of(response)

        for _ in range(3):
            code, response = resume(workspace, session_id, capsys, "--answer", answer("nonsense"))
            assert code == 2, response
            assert cast(dict, cast(dict, response["data"])["question"])["node_id"] == "ASK"

        state = state_of(workspace, session_id)
        assert cast(dict, state["attempt_counters"])["ASK"] == 3
        assert "ASK" not in cast(dict, state["visit_counters"])

    def test_the_answer_event_carries_the_visit_and_the_attempt_ordinals(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, INTERACTIVE_LOOP)
        _, response = start(workspace, capsys)
        session_id = session_id_of(response)

        for text in ("nonsense", "nonsense", "elsewhere", "nonsense", "ok"):
            code, response = resume(workspace, session_id, capsys, "--answer", answer(text))
        assert code == 0, response

        # Each answer says where it happened: two retries inside the first visit, the departure that
        # ended it, then a fresh visit with its own attempt ordinals. The counters themselves keep
        # resetting, which is exactly why the journal has to say it. See ADR 017 §4.
        assert answered_ordinals(state_of(workspace, session_id)) == [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2)]


def session_id_of(response: dict[str, object]) -> str:
    return cast(str, response["session_id"])
