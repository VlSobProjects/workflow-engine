"""Engine behaviour that ADR 002 decides.

These tests build their workflow in the temporary directory, so they do not depend on files outside
the repository.
"""

import json
from pathlib import Path

import pytest

from workflow_engine.actions.action_present import PresentResponse
from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.engine import NO_TRANSITION_ERROR, WorkflowEngine
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import register_function

EXECUTIONS: list[str] = []


@register_function
def count_execution(node_marker: str) -> ActionNodeOutput:
    """Record every execution, so that a retry budget is observable from a test."""
    EXECUTIONS.append(node_marker)
    return ActionNodeOutput(output_text="counted")


COMPONENT_REPORT = False


def create_engine(tmp_path: Path) -> WorkflowEngine:
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=str(tmp_path)))
    engine = bootstrap.build_engine()
    global COMPONENT_REPORT
    if not COMPONENT_REPORT:
        print("\n" + engine.components_report())
        COMPONENT_REPORT = True
    return engine

@pytest.fixture
def load_engine(tmp_path):
    return create_engine(tmp_path)


def counting_node(node_id: str) -> dict[str, object]:
    return {
        "id": node_id,
        "action_type": "function",
        "action_parameters": {
            "function_name": "count_execution",
            "function_parameters": {"node_marker": node_id},
        },
    }


def create_folder_node(node_id: str, work_dir: Path, folder_name: str) -> dict[str, object]:
    return {
        "id": node_id,
        "action_type": "function",
        "action_parameters": {
            "function_name": "create_folder",
            "function_parameters": {"path_target": str(work_dir), "folder_name": folder_name},
        },
    }


def engine_for(
    engine: WorkflowEngine, tmp_path: Path, nodes: list[dict[str, object]]
) -> tuple[PresentResponse, StateModel | None]:
    workflow = {
        "schema_version": "1",
        "flow_id": "guard-flow",
        "start_node_id": nodes[0]["id"],
        "nodes": nodes,
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    workflow_file = tmp_path / "source_workflow.json"
    with workflow_file.open("w") as f:
        json.dump(workflow, f)
    session_id = engine.init_new_session(workflow_file)
    assert session_id
    return engine.start_workflow(session_id=session_id)


def test_passing_post_condition_ends_the_workflow(load_engine, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["validators"] = [{"function_name": "is_output_exist_folder"}]
    response, _ = engine_for(load_engine, tmp_path, [node])

    assert response.title == "Loop finished"
    assert (tmp_path / "made").is_dir()


def test_guard_results_are_recorded_in_the_state(load_engine, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["validators"] = [{"function_name": "is_output_exist_folder"}]
    _, state = engine_for(load_engine, tmp_path, [node])
    assert state
    records = state.guard_results["NODE_1"]
    assert [record.name for record in records] == ["no_error", "not is_output_exist_folder", "all_of"]
    assert [record.passed for record in records] == [True, False, False]


def test_failing_post_condition_fails_the_node(load_engine, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["validators"] = [{"function_name": "is_output_exist_file"}]
    response, state = engine_for(load_engine, tmp_path, [node])

    assert state
    assert response.title == "Node failed"
    assert response.errors is not None
    assert "is_output_exist_file" in response.errors["NODE_1"]
    assert state.error_code == "is_output_exist_file"


def test_declared_route_that_matches_nothing_fails_the_node(load_engine, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["transitions"] = [{"next": "NODE_1", "validator": {"equals": "never"}}]
    response, _ = engine_for(load_engine, tmp_path, [node])

    assert response.title == "Node failed"
    assert response.errors
    assert NO_TRANSITION_ERROR in response.errors["NODE_1"]


def test_post_condition_does_not_replace_the_error_of_a_failed_action(load_engine, tmp_path):
    node = {
        "id": "NODE_1",
        "action_type": "create_artifact",
        "action_parameters": {"artifact_file": ""},
        "validators": [{"function_name": "is_output_exist_file"}],
        "transitions": [{"errors": ["invalid_artifact_file_name"], "fail": "unrecoverable"}],
    }
    response, state = engine_for(load_engine, tmp_path, [node])

    assert response.title == "Node failed"
    assert response.errors
    assert "unrecoverable" in response.errors["NODE_1"]
    assert state
    records = state.guard_results["NODE_1"]
    assert [record.name for record in records] == ["no_error", "all_of", "errors:invalid_artifact_file_name"]
    assert [record.passed for record in records] == [False, False, True]


def test_unknown_target_is_reported_before_execution(load_engine, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["transitions"] = [{"next": "MISSING"}]
    response, _ = engine_for(load_engine, tmp_path, [node])

    assert response.title == "Error in workflow setup"
    assert not (tmp_path / "made").is_dir()


def test_guard_branches_on_the_error_code(load_engine, tmp_path):
    failing = {
        "id": "NODE_1",
        "action_type": "create_artifact",
        "action_parameters": {"artifact_file": ""},
        "transitions": [{"errors": ["invalid_artifact_file_name"], "next": "NODE_2"}],
    }
    recovery = create_folder_node("NODE_2", tmp_path, "recovered")
    response, _ = engine_for(load_engine, tmp_path, [failing, recovery])

    assert response.title == "Loop finished"
    assert (tmp_path / "recovered").is_dir()


def test_failure_keeps_the_message_the_action_wrote(load_engine, tmp_path):
    node = {
        "id": "NODE_1",
        "action_type": "create_artifact",
        "action_parameters": {"artifact_file": ""},
        "transitions": [{"next": "NODE_1", "validator": {"equals": "never"}}],
    }
    response, state = engine_for(load_engine, tmp_path, [node])

    assert response.title == "Node failed"
    assert state
    assert state.error_code == "invalid_artifact_file_name"
    assert state.error_msg is not None
    assert "Artifact file name is invalid or empty" in state.error_msg


def test_a_self_targeting_transition_is_bounded(load_engine, tmp_path):
    node = counting_node("NODE_1")
    node["transitions"] = [{"next": "NODE_1"}]
    node["max_attempts"] = 2
    response, state = engine_for(load_engine, tmp_path, [node])

    assert response.title == "Node failed"
    assert state
    assert state.error_code == "max_attempts_exceeded"
    assert EXECUTIONS.count("NODE_1") == 3


def test_the_retry_budget_does_not_depend_on_how_the_node_was_entered(load_engine, tmp_path):
    def looping_node() -> dict[str, object]:
        node = counting_node("LOOP")
        node["transitions"] = [{"next": "LOOP"}]
        node["max_attempts"] = 2
        return node

    entry = counting_node("ENTRY")
    entry["transitions"] = [{"next": "LOOP"}]

    engine_for(load_engine, tmp_path / "a", [looping_node()])

    started = EXECUTIONS.count("LOOP")
    EXECUTIONS.clear()


    engine_for(create_engine(tmp_path), tmp_path / "b", [entry, looping_node()])
    entered = EXECUTIONS.count("LOOP")

    assert started == entered == 3


def test_attempts_needs_a_node_target(load_engine, tmp_path):
    node = counting_node("NODE_1")
    node["transitions"] = [{"stop": True, "attempts": True}]

    # Nodes are built before the protected section of the engine, so a configuration error escapes
    # instead of becoming a response. See ADR 001.
    response, _ = engine_for(load_engine, tmp_path, [node])
    assert response.errors
    assert "nothing to retry" in response.errors["NODE_1"]


def test_a_transition_cannot_declare_both_a_guard_and_errors(load_engine, tmp_path):
    node = counting_node("NODE_1")
    node["transitions"] = [{"next": "NODE_1", "validator": {"equals": "x"}, "errors": ["e"]}]
    response, _ = engine_for(load_engine, tmp_path, [node])
    assert response.errors
    assert "cannot declare both" in response.errors["NODE_1"]
    print(f"Configuration error for transition with both guard and errors: {response.errors['NODE_1']}")


def test_a_configuration_error_names_the_declared_transition(load_engine, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["validators"] = [{"function_name": "is_output_exist_folder"}]
    node["transitions"] = [{"next": "MISSING"}]
    response, _ = engine_for(load_engine, tmp_path, [node])

    assert response.title == "Error in workflow setup"
    assert response.errors
    assert "NODE_1 transitions[0]" in response.errors


def test_stop_must_be_a_boolean(load_engine, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["transitions"] = [{"stop": "yes"}]
    response, _ = engine_for(load_engine, tmp_path, [node])
    assert response.errors
    assert "'stop' of type: 'str' expected type: 'bool'" in response.errors["NODE_1"]


def test_a_transition_without_a_target_is_rejected(load_engine, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["transitions"] = [{"stop": False}]
    response, _ = engine_for(load_engine, tmp_path, [node])
    assert response.errors
    assert any(v for v in response.errors.values() if "no target" in v)


def test_stop_ends_the_workflow(load_engine, tmp_path):
    node = counting_node("NODE_1")
    node["transitions"] = [{"stop": True}]
    response, _ = engine_for(load_engine, tmp_path, [node])

    assert response.title == "Loop finished"
    assert EXECUTIONS.count("NODE_1") == 1
