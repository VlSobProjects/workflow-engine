"""A model step inside a real run: routing, the bus, and the trail it leaves. See ADR 014 §1, §4.

The runs go through the installed CLI with the `fake` adapter scripted in the `providers` section of
the engine configuration, so a workflow with model steps is exercised end to end without a network.
What they measure is what only a run can show: that a failure class routes like any other node error,
that a retried call leaves one record per call rather than one overwritten slot, and that the audit
of every call survives the loop that produced it.
"""

import json
from pathlib import Path
from typing import cast

import workflow_engine.providers.fake_provider  # noqa: F401 - registers the `fake` adapter before any test runs
from tests.test_adr021_record_writing import records_of, run_json_cli, session_dir, session_id_of, state_of

SUMMARIZE_FLOW = {
    "schema_version": "1",
    "flow_id": "llm-summarize",
    "start_node_id": "SUMMARIZE",
    "nodes": [
        {
            "id": "SUMMARIZE",
            "action_type": "llm",
            "action_parameters": {
                "provider": "local",
                "prompt": "Summarize the inventory of ${param.subject}.",
                "answer": [{"name": "summary"}],
                "record": True,
            },
            "save_as": "raw_reply",
            "transitions": [{"next": "DONE"}],
        },
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        },
    ],
    "inputs": [{"name": "subject"}],
}

RETRY_FLOW = {
    "schema_version": "1",
    "flow_id": "llm-retry",
    "start_node_id": "CLASSIFY",
    "nodes": [
        {
            "id": "CLASSIFY",
            "action_type": "llm",
            "action_parameters": {
                "provider": "local",
                "prompt": "Classify the document.",
                "answer": [{"name": "category"}, {"name": "pages", "type": "int"}],
                "format": "json",
            },
            "max_attempts": 4,
            "transitions": [
                {"next": "DONE", "guard": {"no_error": True}},
                {"errors": ["transient", "rate_limited"], "next": "CLASSIFY", "attempts": True},
                {"errors": ["llm_answer_invalid"], "next": "CLASSIFY", "attempts": True},
                {"errors": ["context_overflow"], "fail": "document_too_large"},
            ],
        },
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        },
    ],
}

OVERFLOW_FLOW = {
    "schema_version": "1",
    "flow_id": "llm-overflow",
    "start_node_id": "CLASSIFY",
    "nodes": [
        {
            "id": "CLASSIFY",
            "action_type": "llm",
            "action_parameters": {"provider": "local", "prompt": "Classify the document.", "answer": []},
            "transitions": [
                {"next": "DONE", "guard": {"no_error": True}},
                {"errors": ["context_overflow"], "fail": "document_too_large"},
            ],
        },
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        },
    ],
}


def build_workspace(tmp_path: Path, workflow: dict[str, object], replies: list[object]) -> dict[str, str]:
    """A workspace whose engine configuration scripts the `fake` adapter for the whole run."""
    config = tmp_path / "workflow_engine_config.json"
    config.write_text(
        json.dumps(
            {
                "work_dir": (tmp_path / "runtime").as_posix(),
                "external_modules": [],
                "storage": {},
                "providers": {"local": {"adapter": "fake", "model": "small-1", "options": {"replies": replies}}},
            }
        ),
        encoding="utf-8",
    )
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(json.dumps(workflow), encoding="utf-8")
    return {
        "config": config.as_posix(),
        "workflow": workflow_file.as_posix(),
        "runtime": (tmp_path / "runtime").as_posix(),
    }


def run(workspace: dict[str, str], capsys, *inputs: str) -> tuple[int, dict[str, object]]:
    argv = ["run", "--workflow-file", workspace["workflow"], "--config", workspace["config"]]
    for assignment in inputs:
        argv += ["--input", assignment]
    return run_json_cli(argv, capsys)


def llm_records(workspace: dict[str, str], session_id: str) -> list[dict[str, object]]:
    return [record for record in records_of(workspace, session_id) if record["action"] == "llm"]


def artifact_text(response: dict[str, object], name: str) -> str:
    """One artifact of the run, read at the absolute path the response published."""
    artifacts = cast(dict[str, dict[str, str]], cast(dict[str, object], response["data"])["artifacts"])
    return Path(artifacts[name]["path"]).read_text(encoding="utf-8")


def parameters_of(workspace: dict[str, str], response: dict[str, object]) -> dict[str, object]:
    """The bus as the state persists it, by name and decoded value."""
    params = cast(dict[str, dict], state_of(workspace, session_id_of(response))["params"])
    return {name: parameter["value"]["object"] for name, parameter in params.items()}


class TestAModelStepInARun:
    def test_the_reply_lands_on_the_bus_and_the_raw_reply_is_the_output_of_the_node(
        self, tmp_path, capsys, provider_seat_guard
    ):
        workspace = build_workspace(tmp_path, SUMMARIZE_FLOW, ["three folders, 42 files"])

        code, response = run(workspace, capsys, "subject=the archive")

        assert code == 0, response
        parameters = parameters_of(workspace, response)
        assert parameters["summary"] == "three folders, 42 files"
        assert parameters["raw_reply"] == "three folders, 42 files"

    def test_the_prompt_reaches_the_model_with_its_references_resolved(self, tmp_path, capsys, provider_seat_guard):
        workspace = build_workspace(tmp_path, SUMMARIZE_FLOW, [])
        # Nothing scripted: the `fake` adapter answers with the prompt it was sent.
        code, response = run(workspace, capsys, "subject=the archive")

        assert code == 0, response
        assert parameters_of(workspace, response)["summary"] == "Summarize the inventory of the archive."

    def test_the_record_of_the_visit_carries_the_audit_of_the_call(self, tmp_path, capsys, provider_seat_guard):
        workspace = build_workspace(tmp_path, SUMMARIZE_FLOW, ["three folders, 42 files"])

        _, response = run(workspace, capsys, "subject=the archive")

        record = llm_records(workspace, session_id_of(response))[0]
        assert record["details"] == {"provider": "local", "model": "small-1", "status": "answered"}
        assert record["status"] == "completed"
        assert [write["name"] for write in cast(list, record["writes"])] == ["raw_reply", "summary"]

    def test_the_prompt_and_the_reply_are_kept_as_artifacts_of_the_session(self, tmp_path, capsys, provider_seat_guard):
        workspace = build_workspace(tmp_path, SUMMARIZE_FLOW, ["three folders, 42 files"])

        _, response = run(workspace, capsys, "subject=the archive")

        record = llm_records(workspace, session_id_of(response))[0]
        assert sorted(cast(list, record["artifacts"])) == ["SUMMARIZE.prompt.1.1", "SUMMARIZE.reply.1.1"]
        assert artifact_text(response, "SUMMARIZE.prompt.1.1") == "Summarize the inventory of the archive."
        assert artifact_text(response, "SUMMARIZE.reply.1.1") == "three folders, 42 files"


class TestFailuresRouteLikeAnyNodeError:
    def test_a_transient_class_is_retried_by_the_transition_and_then_answered(
        self, tmp_path, capsys, provider_seat_guard
    ):
        workspace = build_workspace(
            tmp_path,
            RETRY_FLOW,
            [
                {"error": "transient", "message": "the server hiccupped"},
                {"error": "rate_limited", "message": "slow down"},
                '{"category": "invoice", "pages": 12}',
            ],
        )

        code, response = run(workspace, capsys)

        assert code == 0, response
        parameters = parameters_of(workspace, response)
        assert parameters["category"] == "invoice"
        assert parameters["pages"] == 12

    def test_every_call_of_a_retried_node_leaves_its_own_record(self, tmp_path, capsys, provider_seat_guard):
        workspace = build_workspace(
            tmp_path,
            RETRY_FLOW,
            [
                {"error": "transient", "message": "the server hiccupped"},
                {"error": "rate_limited", "message": "slow down"},
                '{"category": "invoice", "pages": 12}',
            ],
        )

        _, response = run(workspace, capsys)

        records = llm_records(workspace, session_id_of(response))
        assert [record["error_code"] for record in records] == ["transient", "rate_limited", None]
        assert [record["attempt"] for record in records] == [1, 2, 3]
        assert [cast(dict, record["details"])["status"] for record in records] == ["failed", "failed", "answered"]
        assert [cast(dict, record["details"]).get("error_class") for record in records] == [
            "transient",
            "rate_limited",
            None,
        ]

    def test_a_reply_the_declaration_refuses_is_retried_like_a_provider_failure(
        self, tmp_path, capsys, provider_seat_guard
    ):
        workspace = build_workspace(tmp_path, RETRY_FLOW, ["not json", '{"category": "invoice", "pages": 12}'])

        code, response = run(workspace, capsys)

        assert code == 0, response
        records = llm_records(workspace, session_id_of(response))
        assert [record["error_code"] for record in records] == ["llm_answer_invalid", None]
        assert parameters_of(workspace, response)["category"] == "invoice"

    def test_a_class_the_graph_routes_into_a_failure_fails_the_run(self, tmp_path, capsys, provider_seat_guard):
        workspace = build_workspace(
            tmp_path, OVERFLOW_FLOW, [{"error": "context_overflow", "message": "the prompt is too long"}]
        )

        code, response = run(workspace, capsys)

        assert code == 3, response
        record = llm_records(workspace, session_id_of(response))[0]
        assert record["status"] == "failed"
        assert record["transition"] == {"kind": "fail", "target": "document_too_large"}
        assert record["details"]["error_class"] == "context_overflow"

    def test_an_unconfigured_provider_is_a_setup_error_rather_than_a_routable_failure(
        self, tmp_path, capsys, provider_seat_guard
    ):
        workspace = build_workspace(tmp_path, OVERFLOW_FLOW, [])
        config = Path(workspace["config"])
        config.write_text(
            json.dumps({"work_dir": (tmp_path / "runtime").as_posix(), "storage": {}, "providers": {}}),
            encoding="utf-8",
        )

        code, response = run(workspace, capsys)

        assert code == 4, response


class TestTheTrailIsReadableAfterTheRun:
    def test_show_records_publishes_the_audit_of_every_call(self, tmp_path, capsys, provider_seat_guard):
        workspace = build_workspace(
            tmp_path, RETRY_FLOW, [{"error": "transient", "message": "hiccup"}, '{"category": "a", "pages": 1}']
        )
        _, response = run(workspace, capsys)
        session_id = session_id_of(response)

        code, published = run_json_cli(
            ["show-records", "--session-id", session_id, "--node", "CLASSIFY", "--config", workspace["config"]],
            capsys,
        )

        assert code == 0
        data = cast(dict[str, object], published["data"])
        assert data["count"] == 2
        assert [cast(dict, record)["details"]["error_class"] for record in cast(list, data["records"])[:1]] == [
            "transient"
        ]

    def test_the_state_file_holds_no_second_copy_of_the_audit(self, tmp_path, capsys, provider_seat_guard):
        workspace = build_workspace(tmp_path, SUMMARIZE_FLOW, ["three folders, 42 files"])

        _, response = run(workspace, capsys, "subject=the archive")

        state = (session_dir(workspace, session_id_of(response)) / "state.json").read_text(encoding="utf-8")
        assert "small-1" not in state
