"""Engine behaviour that ADR 002 decides.

These tests build their workflow in the temporary directory, so they do not depend on files outside
the repository.
"""

import importlib
import json
from pathlib import Path

import pytest

from workflow_engine.engine import NO_TRANSITION_ERROR, sart_engine
from workflow_engine.storage.json_storage import JsonStorage


@pytest.fixture
def load_modules():
    importlib.import_module("workflow_engine.codecs.base_codecs")
    importlib.import_module("workflow_engine.validators.output_function_validators")
    importlib.import_module("workflow_engine.actions.base_functions")
    importlib.import_module("workflow_engine.actions.action_nodes")


def create_folder_node(node_id: str, work_dir: Path, folder_name: str) -> dict[str, object]:
    return {
        "id": node_id,
        "action_type": "function",
        "action_parameters": {
            "function_name": "create_folder",
            "function_parameters": {"path_target": str(work_dir), "folder_name": folder_name},
        },
    }


def storage_for(tmp_path: Path, nodes: list[dict[str, object]]) -> JsonStorage:
    workflow = {
        "schema_version": "1",
        "flow_id": "guard-flow",
        "start_node_id": nodes[0]["id"],
        "nodes": nodes,
    }
    workflow_file = tmp_path / "source_workflow.json"
    with workflow_file.open("w") as f:
        json.dump(workflow, f)
    storage = JsonStorage(tmp_path)
    storage.start_workflow(workflow_file)
    return storage


def test_passing_post_condition_ends_the_workflow(load_modules, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["validators"] = [{"function_name": "is_output_exist_folder"}]
    storage = storage_for(tmp_path, [node])

    response = sart_engine(storage, None)

    assert response.title == "Loop finished"
    assert (tmp_path / "made").is_dir()


def test_guard_results_are_recorded_in_the_state(load_modules, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["validators"] = [{"function_name": "is_output_exist_folder"}]
    storage = storage_for(tmp_path, [node])

    sart_engine(storage, None)
    state = storage.load_state()

    records = state.guard_results["NODE_1"]
    assert [record.name for record in records] == ["no_error", "not is_output_exist_folder", "all_of"]
    assert [record.passed for record in records] == [True, False, False]


def test_failing_post_condition_fails_the_node(load_modules, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["validators"] = [{"function_name": "is_output_exist_file"}]
    storage = storage_for(tmp_path, [node])

    response = sart_engine(storage, None)

    assert response.title == "Node failed"
    assert response.errors is not None
    assert "is_output_exist_file" in response.errors["NODE_1"]
    assert storage.load_state().error_code == "is_output_exist_file"


def test_declared_route_that_matches_nothing_fails_the_node(load_modules, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["transitions"] = [{"next": "NODE_1", "validator": {"equals": "never"}}]
    storage = storage_for(tmp_path, [node])

    response = sart_engine(storage, None)

    assert response.title == "Node failed"
    assert NO_TRANSITION_ERROR in response.errors["NODE_1"]


def test_post_condition_does_not_replace_the_error_of_a_failed_action(load_modules, tmp_path):
    node = {
        "id": "NODE_1",
        "action_type": "create_artifact",
        "action_parameters": {"artifact_file": ""},
        "validators": [{"function_name": "is_output_exist_file"}],
        "transitions": [{"errors": ["invalid_artifact_file_name"], "fail": "unrecoverable"}],
    }
    storage = storage_for(tmp_path, [node])

    response = sart_engine(storage, None)

    assert response.title == "Node failed"
    assert "unrecoverable" in response.errors["NODE_1"]
    records = storage.load_state().guard_results["NODE_1"]
    assert [record.name for record in records] == ["no_error", "all_of", "errors:invalid_artifact_file_name"]
    assert [record.passed for record in records] == [False, False, True]


def test_unknown_target_is_reported_before_execution(load_modules, tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["transitions"] = [{"next": "MISSING"}]
    storage = storage_for(tmp_path, [node])

    response = sart_engine(storage, None)

    assert response.title == "Error in workflow setup"
    assert not (tmp_path / "made").is_dir()


def test_guard_branches_on_the_error_code(load_modules, tmp_path):
    failing = {
        "id": "NODE_1",
        "action_type": "create_artifact",
        "action_parameters": {"artifact_file": ""},
        "transitions": [{"errors": ["invalid_artifact_file_name"], "next": "NODE_2"}],
    }
    recovery = create_folder_node("NODE_2", tmp_path, "recovered")
    storage = storage_for(tmp_path, [failing, recovery])

    response = sart_engine(storage, None)

    assert response.title == "Loop finished"
    assert (tmp_path / "recovered").is_dir()
