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


def run_json_cli(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def response_data(response: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], response["data"])


def test_run_workflow(tmp_path: Path, create_config, capsys):
    scan_root = tmp_path / "scan-root"
    create_scan_fixture(scan_root)
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))
    code, response = run_json_cli(
        ["run", "--workflow-file", workflow_path.absolute().as_posix(), "--config", create_config.as_posix()],
        capsys,
    )

    assert code == 0
    assert response["command"] == "run"
    assert response["command_status"] == "completed"
    assert cast(str, response["session_id"])
    assert response["workflow_status"] == "completed"


def test_init_set_limit_resume_and_show_state_workflow(tmp_path: Path, create_config, capsys):
    scan_root = tmp_path / "scan-root"
    create_scan_fixture(scan_root)
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

    code, init_response = run_json_cli(
        [
            "init-new-session",
            "--workflow-file",
            workflow_path.absolute().as_posix(),
            "--max-nodes-visited",
            "5",
            "--config",
            create_config.as_posix(),
        ],
        capsys,
    )
    assert code == 0
    assert init_response["command"] == "init-new-session"
    assert init_response["command_status"] == "completed"
    session_id = cast(str, response_data(init_response)["session_id"])
    assert session_id

    code, paused_response = run_json_cli(
        ["resume", "--session-id", session_id, "--config", create_config.as_posix()],
        capsys,
    )
    assert code == 2
    assert paused_response["command"] == "resume"
    assert paused_response["command_status"] == "completed"
    assert paused_response["workflow_status"] == "paused"
    assert paused_response["event_code"] == "workflow_paused_limit"
    assert cast(str, paused_response["session_id"]) == session_id

    code, limit_response = run_json_cli(
        ["set-limit", "--limit", "100", "--session-id", session_id, "--config", create_config.as_posix()],
        capsys,
    )
    assert code == 0
    assert limit_response["command"] == "set-limit"
    assert limit_response["command_status"] == "completed"
    assert cast(str, limit_response["session_id"]) == session_id

    code, resumed_response = run_json_cli(
        ["resume", "--session-id", session_id, "--config", create_config.as_posix()],
        capsys,
    )
    assert code == 0
    assert resumed_response["command_status"] == "completed"
    assert resumed_response["workflow_status"] == "completed"
    assert cast(str, resumed_response["session_id"]) == session_id

    code, state_response = run_json_cli(
        ["show-state", "--session-id", session_id, "--config", create_config.as_posix()],
        capsys,
    )
    assert code == 0
    assert state_response["command"] == "show-state"
    assert state_response["command_status"] == "completed"
    assert state_response["workflow_status"] == "completed"
    assert cast(str, state_response["session_id"]) == session_id


def test_show_state_text_output_includes_the_session_id(tmp_path: Path, create_config, capsys):
    scan_root = tmp_path / "scan-root"
    create_scan_fixture(scan_root)
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

    code, init_response = run_json_cli(
        [
            "init-new-session",
            "--workflow-file",
            workflow_path.absolute().as_posix(),
            "--max-nodes-visited",
            "5",
            "--config",
            create_config.as_posix(),
        ],
        capsys,
    )
    assert code == 0
    session_id = cast(str, response_data(init_response)["session_id"])

    with pytest.raises(SystemExit) as exc_info:
        main(["show-state", "--session-id", session_id, "--config", create_config.as_posix()])

    output = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "Command: show-state" in output
    assert session_id in output
