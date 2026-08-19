"""Execution of the stop-node actions.

A `stop` node may declare a registered function that runs before the workflow ends. It must be given
the parameters the node declares, resolved like every other action's, and `stop_on_error` inherits
that execution unchanged.
"""

import json
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.engine import WorkflowEngine
from workflow_engine.inputs import parse_input_assignment
from workflow_engine.models.state import WorkflowStatusCode


@pytest.fixture
def engine(tmp_path: Path) -> WorkflowEngine:
    return create_engine(tmp_path)


def _session(engine: WorkflowEngine, tmp_path: Path, nodes: list[dict], inputs: list[dict] | None = None) -> str:
    workflow: dict[str, object] = {
        "schema_version": "1",
        "flow_id": "stop-node",
        "start_node_id": nodes[0]["id"],
        "nodes": nodes,
    }
    if inputs is not None:
        workflow["inputs"] = inputs
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow, indent=2))
    return engine.init_new_session(workflow_path=workflow_path)


def _stop_node(action_type: str, function_parameters: dict, **extra: object) -> dict:
    return {
        "id": "END",
        "action_type": action_type,
        "action_parameters": {
            "function_name": extra.pop("function_name", "copy_file"),
            "function_parameters": function_parameters,
            **extra,
        },
        "transitions": [{"stop": True}],
    }


def test_stop_node_runs_its_function_with_the_declared_parameters(engine, tmp_path):
    """The node declares them, so the function must be called with them and not with nothing."""
    source = tmp_path / "source.txt"
    source.write_text("payload")
    target = tmp_path / "copy.txt"
    session_id = _session(
        engine,
        tmp_path,
        [_stop_node("stop", {"path_source": source.as_posix(), "path_target": target.as_posix()})],
    )

    _, state = engine.start_workflow(session_id=session_id)

    assert target.read_text() == "payload"
    assert state.get_workflow_status_code() is WorkflowStatusCode.COMPLETED


def test_stop_node_resolves_parameter_references(engine, tmp_path):
    """`param.`/`output.`/`artifact.` resolution belongs to every action that runs a function."""
    session_id = _session(
        engine,
        tmp_path,
        [_stop_node("stop", {"value": "param.label"}, function_name="echo_value")],
        inputs=[{"name": "label"}],
    )
    engine.set_inputs(session_id, [parse_input_assignment("label=resolved-value")])

    _, state = engine.start_workflow(session_id=session_id)

    assert state.outputs["END"] == "resolved-value"
    assert state.get_workflow_status_code() is WorkflowStatusCode.COMPLETED


def test_stop_on_error_node_runs_its_function_with_the_declared_parameters(engine, tmp_path):
    """`stop_on_error` inherits the stop-node execution and must inherit the parameters with it."""
    source = tmp_path / "source.txt"
    source.write_text("payload")
    target = tmp_path / "copy.txt"
    session_id = _session(
        engine,
        tmp_path,
        [
            _stop_node(
                "stop_on_error",
                {"path_source": source.as_posix(), "path_target": target.as_posix()},
                error_code="copy_failed",
            )
        ],
    )

    _, state = engine.start_workflow(session_id=session_id)

    assert target.read_text() == "payload"
    assert state.get_workflow_status_code() is WorkflowStatusCode.COMPLETED
