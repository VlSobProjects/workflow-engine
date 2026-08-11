import json
from pathlib import Path

import pytest


from test_adr006_e2e_scan import create_scan_fixture, build_workflow
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

def test_run_workflow(tmp_path: Path, create_config, capsys):
    scan_root = tmp_path / "scan-root"
    create_scan_fixture(scan_root)
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--workflow-file", workflow_path.absolute().as_posix(), "--config", create_config.as_posix(), "--json"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    print("\nCaptured output:\n\n" + captured.out)

def test_init_set_limit_resume_workflow(tmp_path: Path, create_config, capsys):
    scan_root = tmp_path / "scan-root"
    create_scan_fixture(scan_root)
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "init-new-session",
                "--workflow-file", workflow_path.absolute().as_posix(),
                "--max-nodes-visited","5",
                "--config", create_config.as_posix(),
                "--json"
            ]
        )
    assert exc_info.value.code == 0
    data = json.loads(capsys.readouterr().out)
    session_id = data["data"]["session_id"]
    assert session_id
    print("\nCaptured init-new-session output:\n\n" + json.dumps(data, indent=2))
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "resume",
                "--session-id", session_id,
                "--config", create_config.as_posix(),
                "--json"
            ]
        )
    assert exc_info.value.code == 2
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "set-limit",
                "--limit", "100",
                "--session-id", session_id,
                "--config", create_config.as_posix(),
                "--json"
            ]
        )
    assert exc_info.value.code == 2
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "resume",
                "--session-id", session_id,
                "--config", create_config.as_posix(),
                "--json"
            ]
        )
    assert exc_info.value.code == 0
    print("\nCaptured resume output:\n\n" + capsys.readouterr().out)
