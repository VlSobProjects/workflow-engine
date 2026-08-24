"""What the engine appends to the trail, end to end through the CLI. See ADR 021 §1-2.

The state keeps one slot per node and the next visit overwrites it, so a loop erases its own history.
These runs read the stream back from the session directory and check that every concluded visit is
there, in order, naming what took hold.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main

LINEAR_FLOW = {
    "schema_version": "1",
    "flow_id": "records-linear",
    "start_node_id": "INIT",
    "nodes": [
        {
            "id": "INIT",
            "action_type": "function",
            "action_parameters": {"function_name": "init_list_param", "function_parameters": {"param_name": "rows"}},
            "transitions": [{"next": "GREET"}],
        },
        {
            "id": "GREET",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "hello"}},
            "save_as": "greeting",
            "transitions": [{"next": "WRITE"}],
        },
        {
            "id": "WRITE",
            "action_type": "function",
            "action_parameters": {
                "function_name": "write_text_artifact",
                "function_parameters": {"artifact_name": "greeting_file", "text": "param.greeting"},
            },
            "transitions": [{"next": "DONE"}],
        },
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        },
    ],
}

CAPPED_LOOP = {
    "schema_version": "1",
    "flow_id": "records-capped-loop",
    "start_node_id": "LOOP",
    "nodes": [
        {
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

FAILING_FLOW = {
    "schema_version": "1",
    "flow_id": "records-failing",
    "start_node_id": "CHECK",
    "nodes": [
        {
            "id": "CHECK",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "nothing here"}},
            "validators": [{"function_name": "is_output_exist_file"}],
            "transitions": [{"next": "DONE"}],
        },
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        },
    ],
}

INTERACTIVE_FLOW = {
    "schema_version": "1",
    "flow_id": "records-interactive",
    "start_node_id": "ASK",
    "nodes": [
        {
            "id": "ASK",
            "action_type": "ask",
            "action_parameters": {
                "title": "Say the word",
                "instruction": "Answer with ok to finish, anything else to be asked again.",
                "answer": [],
            },
            "max_attempts": 5,
            "transitions": [
                {"next": "DONE", "validator": {"equals": "ok"}},
                {"next": "ASK", "attempts": True},
            ],
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


def session_id_of(response: dict[str, object]) -> str:
    return cast(str, response["session_id"])


def session_dir(workspace: dict[str, str], session_id: str) -> Path:
    return Path(workspace["runtime"]) / "json-storage" / session_id


def records_of(workspace: dict[str, str], session_id: str) -> list[dict[str, object]]:
    path = session_dir(workspace, session_id) / "records.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def state_of(workspace: dict[str, str], session_id: str) -> dict[str, object]:
    path = session_dir(workspace, session_id) / "state.json"
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def start(workspace: dict[str, str], capsys) -> tuple[int, dict[str, object]]:
    return run_json_cli(["run", "--workflow-file", workspace["workflow"], "--config", workspace["config"]], capsys)


def answer(text: str) -> str:
    return json.dumps({"status": "success", "values": {}, "text": text, "actor": "agent:tester"})


class TestConcludedVisits:
    def test_every_concluded_visit_leaves_one_record_in_the_order_it_ran(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        code, response = start(workspace, capsys)

        assert code == 0, response
        records = records_of(workspace, session_id_of(response))
        assert [record["node_id"] for record in records] == ["INIT", "GREET", "WRITE", "DONE"]
        assert all(record["status"] == "completed" for record in records)

    def test_a_record_names_the_action_and_the_function_it_ran(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        _, response = start(workspace, capsys)

        first = records_of(workspace, session_id_of(response))[0]

        assert first["action"] == "function"
        assert first["function"] == "init_list_param"

    def test_the_transition_taken_is_recorded_including_the_end_of_the_workflow(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        _, response = start(workspace, capsys)

        records = records_of(workspace, session_id_of(response))

        assert records[0]["transition"] == {"kind": "node", "target": "GREET"}
        assert records[-1]["transition"] == {"kind": "end", "target": None}

    def test_the_guards_the_visit_evaluated_travel_with_it(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, FAILING_FLOW)
        _, response = start(workspace, capsys)

        records = records_of(workspace, session_id_of(response))

        assert [guard["name"] for guard in cast(list, records[0]["guards"])] == [
            "no_error",
            "not is_output_exist_file",
            "all_of",
        ]

    def test_an_unguarded_transition_records_no_guard_because_none_was_asked(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        _, response = start(workspace, capsys)

        records = records_of(workspace, session_id_of(response))

        assert cast(list, records[0]["guards"]) == []

    def test_the_state_holds_no_records_and_the_stream_is_a_file_of_its_own(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        _, response = start(workspace, capsys)
        session_id = session_id_of(response)

        assert "records" not in state_of(workspace, session_id)
        assert (session_dir(workspace, session_id) / "records.jsonl").is_file()
        assert len(records_of(workspace, session_id)) == 4


class TestWhatTookHold:
    def test_an_applied_parameter_write_is_named_with_its_codec_and_mode_and_no_value(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        _, response = start(workspace, capsys)

        init = records_of(workspace, session_id_of(response))[0]

        assert init["writes"] == [{"name": "rows", "codec": "builtins.list", "mode": "SET"}]

    def test_a_node_output_saved_by_name_is_recorded_as_a_write_of_its_own(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        _, response = start(workspace, capsys)

        greet = records_of(workspace, session_id_of(response))[1]

        assert greet["writes"] == [{"name": "greeting", "codec": "builtins.str", "mode": "SAVE_AS"}]

    def test_a_registered_artifact_is_named_by_the_visit_that_produced_it(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        _, response = start(workspace, capsys)

        write = records_of(workspace, session_id_of(response))[2]

        assert write["artifacts"] == ["greeting_file"]

    def test_no_record_carries_a_written_value(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, LINEAR_FLOW)
        _, response = start(workspace, capsys)

        stream = json.dumps(records_of(workspace, session_id_of(response)))

        assert "hello" not in stream


class TestHistoryTheStateOverwrites:
    def test_a_loop_leaves_one_record_per_pass_with_its_own_visit_ordinal(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, CAPPED_LOOP)
        code, response = start(workspace, capsys)

        assert code == 3, response
        records = records_of(workspace, session_id_of(response))
        loops = [record for record in records if record["node_id"] == "LOOP"]
        assert [record["visit"] for record in loops] == [1, 2, 3, 4]
        # The state keeps one counter and one output slot for the node; the trail keeps every pass.
        state = state_of(workspace, session_id_of(response))
        assert cast(dict, state["visit_counters"])["LOOP"] == 3

    def test_the_entry_refused_by_the_visit_cap_is_recorded_as_the_visit_it_was_not_allowed(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, CAPPED_LOOP)
        _, response = start(workspace, capsys)

        refused = records_of(workspace, session_id_of(response))[-1]

        assert refused["node_id"] == "LOOP"
        assert refused["visit"] == 4
        assert refused["status"] == "failed"
        assert refused["error_code"] == "max_visits_exceeded"
        assert refused["transition"] == {"kind": "fail", "target": "max_visits_exceeded"}

    def test_a_failed_node_is_recorded_with_its_error_code_and_the_failure_it_took(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, FAILING_FLOW)
        code, response = start(workspace, capsys)

        assert code == 3, response
        records = records_of(workspace, session_id_of(response))
        assert [record["node_id"] for record in records] == ["CHECK"]
        assert records[0]["status"] == "failed"
        assert records[0]["error_code"] == "is_output_exist_file"
        assert records[0]["transition"] == {"kind": "fail", "target": "is_output_exist_file"}


class TestPausedVisits:
    def test_a_question_waiting_for_its_answer_has_concluded_nothing_and_leaves_no_record(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, INTERACTIVE_FLOW)
        code, response = start(workspace, capsys)

        assert code == 2, response
        assert records_of(workspace, session_id_of(response)) == []

    def test_the_answered_visit_is_recorded_when_it_concludes_with_the_ordinals_of_the_journal(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, INTERACTIVE_FLOW)
        _, response = start(workspace, capsys)
        session_id = session_id_of(response)

        run_json_cli(
            ["resume", "--session-id", session_id, "--answer", answer("nope"), "--config", workspace["config"]],
            capsys,
        )
        code, final = run_json_cli(
            ["resume", "--session-id", session_id, "--answer", answer("ok"), "--config", workspace["config"]],
            capsys,
        )

        assert code == 0, final
        asks = [record for record in records_of(workspace, session_id) if record["node_id"] == "ASK"]
        assert [(record["visit"], record["attempt"]) for record in asks] == [(1, 1), (1, 2)]
        assert asks[0]["transition"] == {"kind": "node", "target": "ASK"}
        assert asks[1]["transition"] == {"kind": "node", "target": "DONE"}
        answered = [
            cast(dict, event)["details"]
            for event in cast(list, state_of(workspace, session_id)["session_events"])
            if cast(dict, event)["code"] == "interactive_answered"
        ]
        assert [(detail["visit"], detail["attempt"]) for detail in answered] == [(1, 1), (1, 2)]
