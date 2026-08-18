"""ADR 012: setup-time enforcement of unbound required inputs at first start."""

import json
from pathlib import Path
from typing import cast

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.cli.main import main
from workflow_engine.engine import WorkflowEngine
from workflow_engine.exceptions import WorkflowInputError
from workflow_engine.inputs import parse_input_assignment
from workflow_engine.models.state import SessionEventCode


def _make_session(tmp_path: Path, inputs: list[dict]) -> tuple[WorkflowEngine, str]:
    engine = create_engine(tmp_path)
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
    return engine, engine.init_new_session(workflow_path=workflow_path)


def test_unbound_required_input_fails_start_and_journals(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "scan_root", "type": "Path"}])
    with pytest.raises(WorkflowInputError):
        engine.start_workflow(session_id=session_id)
    last = engine.runtime.state.session_events[-1]
    assert last.code == SessionEventCode.WORKFLOW_SETUP_FAILED
    assert last.details["missing_inputs"] == ["scan_root"]


def test_optional_unbound_input_proceeds(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "label", "required": False}])
    _, state = engine.start_workflow(session_id=session_id)
    assert state.get_last_event_code() == SessionEventCode.WORKFLOW_COMPLETED


def test_bound_required_input_completes(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "label"}])
    engine.set_inputs(session_id, [parse_input_assignment("label=hi")])
    _, state = engine.start_workflow(session_id=session_id)
    assert state.get_last_event_code() == SessionEventCode.WORKFLOW_COMPLETED


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "workflow_engine_config.json"
    config_path.write_text(json.dumps({"work_dir": tmp_path.as_posix(), "external_modules": [], "storage": {}}))
    return config_path.absolute()


def test_cli_exit_code_4_for_unbound_required_input(tmp_path, capsys):
    config = _write_config(tmp_path)
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
        "inputs": [{"name": "scan_root", "type": "Path"}],
    }
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow))

    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--workflow-file", workflow_path.as_posix(), "--config", config.as_posix(), "--json"])
    assert cast(int, exc_info.value.code) == 4
