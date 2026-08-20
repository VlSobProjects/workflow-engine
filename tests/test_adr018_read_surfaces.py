"""ADR 018 session read surfaces: what `show-state` still carries, and the three bounded read commands.

The fixture is the shipped `approve-and-copy` template, because it is the one example that leaves a
session with typed parameters, a guarded interactive node and a journal worth reading — the three
things these commands publish. Every case drives the CLI, since the decision is about what a caller
gets back, not about how the state is kept.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main
from workflow_engine.codecs.base_codecs import PathCodec

TEMPLATE = Path(__file__).resolve().parents[1] / "examples" / "approve-and-copy.json"
# The published codec name is the registry key the state persists, whatever `pathlib` calls its
# module in the running interpreter; pinning the literal here would pin a Python version.
PATH_CODEC = PathCodec.type_name()


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
    }


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def run_text_cli(argv: list[str], capsys) -> tuple[int, str]:
    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    return cast(int, exc_info.value.code), capsys.readouterr().out


def paused_session(workspace: dict[str, str], capsys) -> str:
    """A session stopped at `ASK_APPROVAL`: three parameters bound or written, no decision yet."""
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
    return cast(str, response["session_id"])


def completed_session(workspace: dict[str, str], capsys) -> str:
    """The same session carried to completion by an approval, so the guards have answered."""
    session_id = paused_session(workspace, capsys)
    code, _ = run_json_cli(
        [
            "resume",
            "--session-id",
            session_id,
            "--config",
            workspace["config"],
            "--answer",
            json.dumps({"status": "success", "text": "approved", "values": {"reviewer": "ops"}}),
        ],
        capsys,
    )
    assert code == 0
    return session_id


def data_of(response: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], response["data"])


class TestShowState:
    """`show-state` shows the state of the run, and nothing else. See ADR 018 §1."""

    def test_the_removed_fields_are_gone_and_the_bounded_ones_stay(self, workspace, capsys):
        session_id = completed_session(workspace, capsys)

        code, response = run_json_cli(
            ["show-state", "--session-id", session_id, "--config", workspace["config"]], capsys
        )

        assert code == 0
        data = data_of(response)
        assert "parameters" not in data
        assert "outputs" not in data
        assert "inputs" not in data
        assert data["current_node"]
        assert "deliverables" in data
        assert "artifacts" in data
        assert "artifacts_absolute" in data
        assert "artifacts_path" in data

    def test_the_guard_traces_join_the_result(self, workspace, capsys):
        """The record of why the run stands where it stands, bounded by the latest attempt per node."""
        session_id = completed_session(workspace, capsys)

        _, response = run_json_cli(["show-state", "--session-id", session_id, "--config", workspace["config"]], capsys)

        guard_results = cast(dict[str, list[dict[str, object]]], data_of(response)["guard_results"])
        assert {"name": "equals:approved", "passed": True} in guard_results["ASK_APPROVAL"]

    def test_a_paused_run_still_reports_exit_code_zero(self, workspace, capsys):
        """An info command answers about the run without taking the run's exit code. See ADR 018 §4."""
        session_id = paused_session(workspace, capsys)

        code, response = run_json_cli(
            ["show-state", "--session-id", session_id, "--config", workspace["config"]], capsys
        )

        assert code == 0
        assert response["workflow_status"] == "paused"


class TestListParameters:
    """`list-parameters` names the parameters and their types, never their values. See ADR 018 §2."""

    def test_it_lists_name_type_and_writing_node_without_values(self, workspace, capsys):
        session_id = completed_session(workspace, capsys)

        code, response = run_json_cli(
            ["list-parameters", "--session-id", session_id, "--config", workspace["config"]], capsys
        )

        assert code == 0
        data = data_of(response)
        parameters = cast(list[dict[str, str]], data["parameters"])
        assert data["count"] == len(parameters)
        by_name = {parameter["name"]: parameter for parameter in parameters}
        assert by_name["source_file"]["type"] == PATH_CODEC
        assert by_name["source_size"]["source_node"] == "READ_SIZE"
        assert by_name["reviewer"]["source_node"] == "ASK_APPROVAL"
        assert all(set(parameter) == {"name", "type", "source_node"} for parameter in parameters)
        assert workspace["source"] not in json.dumps(data)

    def test_the_text_form_carries_one_line_per_parameter(self, workspace, capsys):
        session_id = paused_session(workspace, capsys)

        code, output = run_text_cli(
            ["list-parameters", "--session-id", session_id, "--config", workspace["config"]], capsys
        )

        assert code == 0
        assert f"Parameters of session {session_id} (3):" in output
        assert f"- source_file: {PATH_CODEC} (written by READ_SIZE)" in output

    def test_an_unknown_session_is_a_command_error(self, workspace, capsys):
        code, response = run_json_cli(
            ["list-parameters", "--session-id", "no-such-session", "--config", workspace["config"]], capsys
        )

        assert code == 4
        assert response["command_status"] == "error"


class TestShowParameter:
    """`show-parameter` returns one value: rendered as text, or as the persisted envelope. ADR 018 §2."""

    def test_the_text_form_is_the_single_rendering_rule(self, workspace, capsys):
        """A path prints in POSIX form on every OS, as ADR 016 requires of every published value."""
        session_id = paused_session(workspace, capsys)

        code, output = run_text_cli(
            ["show-parameter", "--session-id", session_id, "--name", "source_file", "--config", workspace["config"]],
            capsys,
        )

        assert code == 0
        assert f"Message: {Path(workspace['source']).as_posix()}" in output

    def test_the_json_form_carries_the_codec_envelope(self, workspace, capsys):
        session_id = paused_session(workspace, capsys)

        code, response = run_json_cli(
            ["show-parameter", "--session-id", session_id, "--name", "source_file", "--config", workspace["config"]],
            capsys,
        )

        assert code == 0
        assert data_of(response) == {
            "name": "source_file",
            "source_node": "READ_SIZE",
            "value": {"object": Path(workspace["source"]).as_posix(), "object_type": PATH_CODEC},
        }

    def test_the_envelope_value_feeds_set_input_of_another_session(self, workspace, capsys):
        """The point of publishing the envelope: a typed value crosses to another session unchanged."""
        source_session = paused_session(workspace, capsys)
        _, read = run_json_cli(
            [
                "show-parameter",
                "--session-id",
                source_session,
                "--name",
                "source_file",
                "--config",
                workspace["config"],
            ],
            capsys,
        )
        encoded = cast(dict[str, object], data_of(read)["value"])

        _, init = run_json_cli(
            ["init-new-session", "--workflow-file", TEMPLATE.as_posix(), "--config", workspace["config"]], capsys
        )
        target_session = cast(str, data_of(init)["session_id"])
        code, response = run_json_cli(
            [
                "set-input",
                "--session-id",
                target_session,
                "--config",
                workspace["config"],
                "--input",
                f"source_file:{encoded['object_type']}={encoded['object']}",
            ],
            capsys,
        )

        assert code == 0
        assert data_of(response)["inputs_set"] == ["source_file"]

    def test_an_unknown_name_is_a_resolution_error(self, workspace, capsys):
        """An empty success would hide a typo from a script, so the command fails like `help-component`."""
        session_id = paused_session(workspace, capsys)

        code, response = run_json_cli(
            ["show-parameter", "--session-id", session_id, "--name", "no_such_param", "--config", workspace["config"]],
            capsys,
        )

        assert code == 4
        assert response["command_status"] == "error"
        assert cast(dict[str, str], response["errors"])["parameter"] == "no_such_param not found"


class TestShowJournal:
    """`show-journal` publishes the journal, whole unless the caller bounds it. See ADR 018 §3."""

    def test_without_flags_the_whole_journal_is_returned(self, workspace, capsys):
        session_id = completed_session(workspace, capsys)

        code, response = run_json_cli(
            ["show-journal", "--session-id", session_id, "--config", workspace["config"]], capsys
        )

        assert code == 0
        data = data_of(response)
        events = cast(list[dict[str, object]], data["events"])
        assert data["count"] == data["total"] == len(events)
        codes = [event["code"] for event in events]
        assert codes[0] == "session_created"
        assert "interactive_answered" in codes
        assert codes[-1] == "workflow_completed"
        assert all(set(event) == {"timestamp", "code", "actor", "event_id", "details"} for event in events)

    def test_the_journal_names_values_never_carries_them(self, workspace, capsys):
        """A read surface publishes what is persisted, and the journal keeps no values (ADR 013 §9)."""
        session_id = completed_session(workspace, capsys)

        _, response = run_json_cli(
            ["show-journal", "--session-id", session_id, "--config", workspace["config"]], capsys
        )

        answered = [
            event
            for event in cast(list[dict[str, object]], data_of(response)["events"])
            if event["code"] == "interactive_answered"
        ]
        details = cast(dict[str, object], answered[0]["details"])
        assert details["names"] == ["reviewer"]
        assert "ops" not in json.dumps(details)

    def test_tail_bounds_the_answer_and_the_total_still_reports_the_whole(self, workspace, capsys):
        session_id = completed_session(workspace, capsys)
        _, whole = run_json_cli(["show-journal", "--session-id", session_id, "--config", workspace["config"]], capsys)
        total = cast(int, data_of(whole)["total"])

        code, response = run_json_cli(
            ["show-journal", "--session-id", session_id, "--tail", "2", "--config", workspace["config"]], capsys
        )

        assert code == 0
        data = data_of(response)
        assert data["count"] == 2
        assert data["total"] == total
        assert data["events"] == cast(list, data_of(whole)["events"])[-2:]

    def test_node_filters_to_the_events_that_name_the_node(self, workspace, capsys):
        session_id = completed_session(workspace, capsys)

        code, response = run_json_cli(
            ["show-journal", "--session-id", session_id, "--node", "ASK_APPROVAL", "--config", workspace["config"]],
            capsys,
        )

        assert code == 0
        events = cast(list[dict[str, object]], data_of(response)["events"])
        assert events
        assert all(cast(dict, event["details"])["node_id"] == "ASK_APPROVAL" for event in events)

    def test_tail_and_node_compose(self, workspace, capsys):
        """The filter runs first, so the pair reads as "the last n events of this node"."""
        session_id = completed_session(workspace, capsys)
        _, filtered = run_json_cli(
            ["show-journal", "--session-id", session_id, "--node", "ASK_APPROVAL", "--config", workspace["config"]],
            capsys,
        )

        _, response = run_json_cli(
            [
                "show-journal",
                "--session-id",
                session_id,
                "--node",
                "ASK_APPROVAL",
                "--tail",
                "1",
                "--config",
                workspace["config"],
            ],
            capsys,
        )

        assert data_of(response)["events"] == cast(list, data_of(filtered)["events"])[-1:]

    def test_a_non_positive_tail_is_a_command_error(self, workspace, capsys):
        """`--tail 0` would answer with nothing at all, which reads as an empty journal."""
        session_id = paused_session(workspace, capsys)

        code, response = run_json_cli(
            ["show-journal", "--session-id", session_id, "--tail", "0", "--config", workspace["config"]], capsys
        )

        assert code == 4
        assert response["command_status"] == "error"

    def test_the_text_form_carries_one_line_per_event(self, workspace, capsys):
        session_id = paused_session(workspace, capsys)

        code, output = run_text_cli(
            ["show-journal", "--session-id", session_id, "--tail", "1", "--config", workspace["config"]], capsys
        )

        assert code == 0
        assert f"Journal of session {session_id} (1 of " in output
        assert "workflow_paused_interactive" in output
