"""ADR 012: the set-input command, the one-shot run --input form, and the removed resume flags."""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "workflow_engine_config.json"
    config_path.write_text(json.dumps({"work_dir": tmp_path.as_posix(), "external_modules": [], "storage": {}}))
    return config_path.absolute()


def _write_workflow(tmp_path: Path, inputs: list[dict]) -> Path:
    workflow = {
        "schema_version": "1",
        "flow_id": "f",
        "start_node_id": "N",
        "nodes": [
            {
                "id": "N",
                "action_type": "function",
                "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "x"}},
                "transitions": [{"stop": True}],
            }
        ],
        "inputs": inputs,
    }
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow))
    return workflow_path


def test_set_input_binds_and_reports(tmp_path, capsys):
    config = _write_config(tmp_path)
    workflow_path = _write_workflow(tmp_path, [{"name": "label"}])
    code, init_response = run_json_cli(
        ["init-new-session", "--workflow-file", workflow_path.as_posix(), "--config", config.as_posix()], capsys
    )
    session_id = cast(str, cast(dict, init_response["data"])["session_id"])

    code, response = run_json_cli(
        ["set-input", "--session-id", session_id, "--input", "label=hi", "--config", config.as_posix()], capsys
    )
    assert code == 0
    data = cast(dict, response["data"])
    assert data["inputs_set"] == ["label"]
    assert [item["name"] for item in cast(list, data["inputs"])] == ["label"]


def test_two_step_flow_completes(tmp_path, capsys):
    config = _write_config(tmp_path)
    workflow_path = _write_workflow(tmp_path, [{"name": "label"}])
    _, init_response = run_json_cli(
        ["init-new-session", "--workflow-file", workflow_path.as_posix(), "--config", config.as_posix()], capsys
    )
    session_id = cast(str, cast(dict, init_response["data"])["session_id"])
    run_json_cli(
        ["set-input", "--session-id", session_id, "--input", "label=hi", "--config", config.as_posix()], capsys
    )
    code, response = run_json_cli(["resume", "--session-id", session_id, "--config", config.as_posix()], capsys)
    assert code == 0
    assert response["workflow_status"] == "completed"


def test_run_one_shot_with_input(tmp_path, capsys):
    config = _write_config(tmp_path)
    workflow_path = _write_workflow(tmp_path, [{"name": "label"}])
    code, response = run_json_cli(
        ["run", "--workflow-file", workflow_path.as_posix(), "--input", "label=hi", "--config", config.as_posix()],
        capsys,
    )
    assert code == 0
    assert response["workflow_status"] == "completed"


def test_undeclared_input_is_command_error(tmp_path, capsys):
    config = _write_config(tmp_path)
    workflow_path = _write_workflow(tmp_path, [{"name": "label"}])
    _, init_response = run_json_cli(
        ["init-new-session", "--workflow-file", workflow_path.as_posix(), "--config", config.as_posix()], capsys
    )
    session_id = cast(str, cast(dict, init_response["data"])["session_id"])
    code, response = run_json_cli(
        ["set-input", "--session-id", session_id, "--input", "other=hi", "--config", config.as_posix()], capsys
    )
    assert code == 4
    assert response["command_status"] == "error"


def test_resume_works_with_only_session_id(tmp_path, capsys):
    config = _write_config(tmp_path)
    workflow_path = _write_workflow(tmp_path, [])
    _, init_response = run_json_cli(
        ["init-new-session", "--workflow-file", workflow_path.as_posix(), "--config", config.as_posix()], capsys
    )
    session_id = cast(str, cast(dict, init_response["data"])["session_id"])
    code, response = run_json_cli(["resume", "--session-id", session_id, "--config", config.as_posix()], capsys)
    assert code == 0
    assert response["workflow_status"] == "completed"


@pytest.mark.parametrize("flag", ["--param-name", "--param-value", "--write-mode", "--error-code", "--artifact-name"])
def test_removed_resume_flags_are_rejected(flag, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["resume", "--session-id", "X", flag, "value"])
    assert cast(int, exc_info.value.code) == 4
