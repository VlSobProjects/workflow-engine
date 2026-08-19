"""CLI contract tests: negative scenarios, edge cases, and schema consistency.

Tests are organized by command and cover:
- missing required arguments
- invalid arguments
- setup failures
- command-specific output contracts
"""

import json
from pathlib import Path
from typing import cast

import pytest

from tests.test_adr006_e2e_scan import build_workflow, create_scan_fixture
from workflow_engine.cli.main import main


@pytest.fixture
def create_config(tmp_path: Path):
    config_path = tmp_path / "workflow_engine_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_data = {
        "work_dir": tmp_path.as_posix(),
        "external_modules": [],
        "storage": {},
    }
    with config_path.open("w") as f:
        json.dump(config_data, f)
    return config_path.absolute()


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    """Run CLI with --json flag and capture exit code and parsed output."""
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def build_failing_workflow(root: Path) -> dict[str, object]:
    """A one-node workflow that fails the node: the folder the copy target lives in does not exist."""
    (root / "source.txt").write_text("payload")
    return {
        "schema_version": "1",
        "flow_id": "cli-contract-failing",
        "start_node_id": "COPY_TO_MISSING_FOLDER",
        "nodes": [
            {
                "id": "COPY_TO_MISSING_FOLDER",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "copy_file",
                    "function_parameters": {
                        "path_source": (root / "source.txt").as_posix(),
                        "path_target": (root / "missing-folder" / "source.txt").as_posix(),
                    },
                },
                "transitions": [{"errors": ["target_folder_not_found"]}],
            },
        ],
    }


def build_exception_workflow(root: Path) -> dict[str, object]:
    """A one-node workflow whose action raises: the source file the copy reads does not exist."""
    return {
        "schema_version": "1",
        "flow_id": "cli-contract-exception",
        "start_node_id": "COPY_MISSING_SOURCE",
        "nodes": [
            {
                "id": "COPY_MISSING_SOURCE",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "copy_file",
                    "function_parameters": {
                        "path_source": (root / "no-such-source.txt").as_posix(),
                        "path_target": (root / "copy.txt").as_posix(),
                    },
                },
                "transitions": [{"stop": True}],
            },
        ],
    }


class TestRunCommand:
    """Tests for `run` command."""

    def test_run_with_missing_workflow_file(self, create_config, capsys):
        """Missing workflow file should return error exit code 4."""
        code, response = run_json_cli(
            ["run", "--workflow-file", "/nonexistent/workflow.json", "--config", create_config.as_posix()],
            capsys,
        )
        assert code == 4
        assert response["command_status"] == "error"
        assert response["command"] == "run"

    def test_run_json_response_has_all_required_fields(self, tmp_path: Path, create_config, capsys):
        """run command JSON response must have command, command_status,
        workflow_status, event_code, message, errors, data."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        code, response = run_json_cli(
            ["run", "--workflow-file", workflow_path.as_posix(), "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        required_fields = {
            "command",
            "command_status",
            "workflow_status",
            "event_code",
            "message",
            "errors",
            "data",
            "session_id",
        }
        assert set(response.keys()) == required_fields
        assert response["command"] == "run"
        assert response["command_status"] == "completed"
        assert isinstance(response["data"], dict)
        assert isinstance(response["session_id"], str)

    def test_successful_run_reports_no_errors(self, tmp_path: Path, create_config, capsys):
        """A non-empty `errors` map means something failed; a completed run must leave it empty."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        code, response = run_json_cli(
            ["run", "--workflow-file", workflow_path.as_posix(), "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        assert response["workflow_status"] == "completed"
        assert not response["errors"]

    def test_run_of_a_failing_workflow_writes_nothing_but_json_to_stdout(self, tmp_path: Path, create_config, capsys):
        """A failed run stays machine readable: the engine reports the failure through the response only."""
        workflow_path = tmp_path / "failing_workflow.json"
        workflow_path.write_text(json.dumps(build_failing_workflow(tmp_path), indent=2))

        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "run",
                    "--workflow-file",
                    workflow_path.as_posix(),
                    "--config",
                    create_config.as_posix(),
                    "--json",
                ]
            )

        stdout = capsys.readouterr().out
        response = cast(dict[str, object], json.loads(stdout))
        code = exc_info.value.code

        assert code == 3
        assert response["command_status"] == "completed"
        assert response["workflow_status"] == "failed"
        assert "target_folder_not_found" in cast(dict[str, str], response["errors"])["COPY_TO_MISSING_FOLDER"]

    def test_run_that_ends_in_an_exception_reports_the_cause_in_errors(self, tmp_path: Path, create_config, capsys):
        """An exception leaves no node error in the state, so the engine response carries the cause."""
        workflow_path = tmp_path / "exception_workflow.json"
        workflow_path.write_text(json.dumps(build_exception_workflow(tmp_path), indent=2))

        code, response = run_json_cli(
            ["run", "--workflow-file", workflow_path.as_posix(), "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 3
        assert response["workflow_status"] == "failed"
        errors = cast(dict[str, str], response["errors"])
        assert [key for key in errors if "FunctionRuntimeError" in key]


class TestInitNewSessionCommand:
    """Tests for `init-new-session` command."""

    def test_init_with_missing_workflow_file(self, create_config, capsys):
        """Missing workflow file should return error exit code 4."""
        code, response = run_json_cli(
            ["init-new-session", "--workflow-file", "/nonexistent/workflow.json", "--config", create_config.as_posix()],
            capsys,
        )
        assert code == 4
        assert response["command_status"] == "error"
        assert response["command"] == "init-new-session"

    def test_init_reports_the_session_id_at_top_level(self, tmp_path: Path, create_config, capsys):
        """init-new-session must fill the top-level session_id field like every other command."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        code, response = run_json_cli(
            ["init-new-session", "--workflow-file", workflow_path.as_posix(), "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        assert isinstance(response["session_id"], str)
        assert response["session_id"] == cast(dict[str, object], response["data"])["session_id"]

    def test_init_with_invalid_max_nodes_visited(self, tmp_path: Path, create_config, capsys):
        """Non-numeric max-nodes-visited should fail at parser level."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "init-new-session",
                    "--workflow-file",
                    workflow_path.as_posix(),
                    "--max-nodes-visited",
                    "not_a_number",
                    "--config",
                    create_config.as_posix(),
                    "--json",
                ]
            )

        assert exc_info.value.code == 4


class TestResumeCommand:
    """Tests for `resume` command."""

    def test_resume_with_unknown_session_id(self, create_config, capsys):
        """Unknown session ID should return error exit code 4."""
        code, response = run_json_cli(
            ["resume", "--session-id", "unknown-session-id", "--config", create_config.as_posix()],
            capsys,
        )
        assert code == 4
        assert response["command_status"] == "error"
        assert response["command"] == "resume"

    def test_resume_json_response_has_workflow_status(self, tmp_path: Path, create_config, capsys):
        """resume command response must include workflow_status and session_id at top level."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        code, init_response = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                workflow_path.as_posix(),
                "--max-nodes-visited",
                "5",
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )
        session_id = cast(str, cast(dict[str, object], init_response["data"])["session_id"])

        code, response = run_json_cli(
            ["resume", "--session-id", session_id, "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 2
        assert response["workflow_status"] in ["completed", "paused", "failed"]
        assert isinstance(response["session_id"], str)
        assert response["session_id"] == session_id


class TestSetLimitCommand:
    """Tests for `set-limit` command."""

    def test_set_limit_with_unknown_session_id(self, create_config, capsys):
        """Unknown session ID should return error exit code 4."""
        code, response = run_json_cli(
            ["set-limit", "--session-id", "unknown-session-id", "--limit", "100", "--config", create_config.as_posix()],
            capsys,
        )
        assert code == 4
        assert response["command_status"] == "error"
        assert response["command"] == "set-limit"

    def test_set_limit_with_invalid_limit(self, tmp_path: Path, create_config, capsys):
        """Non-numeric limit should fail at parser level."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        _, init_response = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                workflow_path.as_posix(),
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )
        session_id = cast(str, cast(dict[str, object], init_response["data"])["session_id"])

        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "set-limit",
                    "--session-id",
                    session_id,
                    "--limit",
                    "not_a_number",
                    "--config",
                    create_config.as_posix(),
                    "--json",
                ]
            )

        assert exc_info.value.code == 4

    def test_set_limit_always_returns_exit_code_0(self, tmp_path: Path, create_config, capsys):
        """set-limit is not a runner command; even on paused workflow it returns 0."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        _, init_response = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                workflow_path.as_posix(),
                "--max-nodes-visited",
                "5",
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )
        session_id = cast(str, cast(dict[str, object], init_response["data"])["session_id"])

        run_json_cli(
            ["resume", "--session-id", session_id, "--config", create_config.as_posix()],
            capsys,
        )

        code, response = run_json_cli(
            ["set-limit", "--limit", "100", "--session-id", session_id, "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        assert response["command_status"] == "completed"

    def test_set_limit_zero_reports_the_hard_safety_cap(self, tmp_path: Path, create_config, capsys):
        """Soft unlimited mode must state explicitly that the run stays bounded by the hard cap."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        _, init_response = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                workflow_path.as_posix(),
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )
        session_id = cast(str, cast(dict[str, object], init_response["data"])["session_id"])

        code, response = run_json_cli(
            ["set-limit", "--limit", "0", "--session-id", session_id, "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        assert "hard_max_nodes_visited=1000" in cast(str, response["message"])


class TestShowStateCommand:
    """Tests for `show-state` command."""

    def test_show_state_with_unknown_session_id(self, create_config, capsys):
        """Unknown session ID should return error exit code 4."""
        code, response = run_json_cli(
            ["show-state", "--session-id", "unknown-session-id", "--config", create_config.as_posix()],
            capsys,
        )
        assert code == 4
        assert response["command_status"] == "error"
        assert response["command"] == "show-state"

    def test_show_state_returns_full_data(self, tmp_path: Path, create_config, capsys):
        """show-state must return full state data including artifacts, parameters, outputs."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        code, init_response = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                workflow_path.as_posix(),
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )
        session_id = cast(str, cast(dict[str, object], init_response["data"])["session_id"])

        run_json_cli(
            ["resume", "--session-id", session_id, "--config", create_config.as_posix()],
            capsys,
        )

        code, response = run_json_cli(
            ["show-state", "--session-id", session_id, "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        data = cast(dict[str, object], response["data"])
        assert "artifacts" in data
        assert "parameters" in data
        assert "outputs" in data


class TestListSessionsCommand:
    """Tests for `list-sessions` command."""

    def test_list_sessions_returns_exit_code_0(self, create_config, capsys):
        """list-sessions is not a runner command; always returns 0."""
        code, response = run_json_cli(
            ["list-sessions", "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        assert response["command_status"] == "completed"
        assert response["command"] == "list-sessions"

    def test_list_sessions_returns_sessions_array(self, tmp_path: Path, create_config, capsys):
        """list-sessions must return data.sessions as array."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        code, init_response = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                workflow_path.as_posix(),
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )
        session_id = cast(str, cast(dict[str, object], init_response["data"])["session_id"])

        code, response = run_json_cli(
            ["list-sessions", "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        data = cast(dict[str, object], response["data"])
        sessions = cast(list[str], data["sessions"])
        assert isinstance(sessions, list)
        assert session_id in sessions


class TestHelpComponentsCommand:
    """Tests for `help-components` command."""

    def test_help_components_returns_exit_code_0(self, create_config, capsys):
        """help-components is not a runner command; always returns 0."""
        code, response = run_json_cli(
            ["help-components", "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        assert response["command_status"] == "completed"
        assert response["command"] == "help-components"

    def test_help_components_returns_contract_payload(self, create_config, capsys):
        """help-components must return contract_version and normalized component type keys."""
        code, response = run_json_cli(
            ["help-components", "--config", create_config.as_posix()],
            capsys,
        )

        assert code == 0
        data = cast(dict[str, object], response["data"])
        assert data["contract_version"] == "1.0"
        components = cast(dict[str, object], data["components"])
        assert set(components.keys()) == {"actions", "functions", "validators", "guards", "codecs"}
        for items in components.values():
            assert isinstance(items, list)
            for item in cast(list[dict[str, object]], items):
                assert set(item.keys()) == {"name", "summary", "source"}


class TestHelpComponentCommand:
    """Tests for `help-component` command."""

    def test_help_component_returns_detail_payload(self, create_config, capsys):
        code, response = run_json_cli(
            [
                "help-component",
                "--component-type",
                "actions",
                "--component-name",
                "function",
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )

        assert code == 0
        data = cast(dict[str, object], response["data"])
        assert data["contract_version"] == "1.0"
        component = cast(dict[str, object], data["component"])
        assert {"name", "type", "summary", "description", "parameters", "source", "notes"} <= set(component.keys())
        assert component["name"] == "function"
        assert component["type"] == "action"

    def test_help_component_without_name_returns_type_payload(self, create_config, capsys):
        """help-component with only a type describes the type and lists its components."""
        code, response = run_json_cli(
            [
                "help-component",
                "--component-type",
                "actions",
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )

        assert code == 0
        assert response["command_status"] == "completed"
        data = cast(dict[str, object], response["data"])
        assert data["contract_version"] == "1.0"
        block = cast(dict[str, object], data["component_type"])
        assert set(block.keys()) == {"type", "description", "components"}
        assert block["type"] == "actions"
        assert block["description"]
        components = cast(list[dict[str, object]], block["components"])
        assert components
        for item in components:
            assert set(item.keys()) == {"name", "summary", "source"}
        assert "function" in {item["name"] for item in components}

    def test_help_component_unknown_name_returns_exit_code_4(self, create_config, capsys):
        code, response = run_json_cli(
            [
                "help-component",
                "--component-type",
                "actions",
                "--component-name",
                "no-such-action",
                "--config",
                create_config.as_posix(),
            ],
            capsys,
        )

        assert code == 4
        assert response["command_status"] == "error"
        assert response["errors"]


class TestMalformedCommandLine:
    """A wrong call is the most common error of all: stdout must stay parseable."""

    def test_unknown_command_writes_nothing_to_stdout(self, capsys):
        """Without --json a malformed call reports on stderr and leaves stdout empty."""
        with pytest.raises(SystemExit) as exc_info:
            main(["no-such-command"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 4
        assert captured.out == ""
        assert "usage:" in captured.err

    def test_missing_required_option_writes_nothing_to_stdout(self, capsys):
        """A known command missing a required option reports on stderr, not on stdout."""
        with pytest.raises(SystemExit) as exc_info:
            main(["run"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 4
        assert captured.out == ""
        assert "--workflow-file" in captured.err

    def test_missing_required_option_with_json_returns_a_command_result(self, capsys):
        """With --json stdout carries exactly one CommandResult naming the command that failed."""
        with pytest.raises(SystemExit) as exc_info:
            main(["run", "--json"])

        captured = capsys.readouterr()
        response = cast(dict[str, object], json.loads(captured.out))
        assert exc_info.value.code == 4
        assert response["command"] == "run"
        assert response["command_status"] == "error"
        assert response["message"]
        assert cast(dict[str, str], response["errors"])["command_line"]
        assert "usage:" in captured.err

    def test_unknown_command_with_json_returns_a_command_result_without_a_command(self, capsys):
        """A command line too malformed to name a command still answers in JSON, with command null."""
        with pytest.raises(SystemExit) as exc_info:
            main(["no-such-command", "--json"])

        captured = capsys.readouterr()
        response = cast(dict[str, object], json.loads(captured.out))
        assert exc_info.value.code == 4
        assert response["command"] is None
        assert response["command_status"] == "error"


class TestCliOutputSchema:
    """Tests for JSON/text output schema consistency across all commands."""

    def test_all_commands_have_consistent_json_schema(self, tmp_path: Path, create_config, capsys):
        """All command responses must have: command, command_status, message, errors, data."""
        scan_root = tmp_path / "scan-root"
        create_scan_fixture(scan_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

        commands = [
            ["init-new-session", "--workflow-file", workflow_path.as_posix(), "--config", create_config.as_posix()],
            ["run", "--workflow-file", workflow_path.as_posix(), "--config", create_config.as_posix()],
            ["list-sessions", "--config", create_config.as_posix()],
            ["help-components", "--config", create_config.as_posix()],
        ]

        for cmd in commands:
            _, response = run_json_cli(cmd, capsys)
            assert "command" in response
            assert "command_status" in response
            assert "message" in response
            assert "errors" in response
            assert "data" in response
            assert response["command_status"] in ["completed", "error"]
