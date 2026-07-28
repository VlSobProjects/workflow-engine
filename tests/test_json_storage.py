import datetime
import json
from pathlib import Path

import pytest

from workflow_engine.exceptions import StateError
from workflow_engine.models.state import ActionParameter, StateModel
from workflow_engine.storage.json_storage import JsonStateStorage


@pytest.fixture
def state(tmp_path):
    return StateModel(
        timestamp=datetime.datetime.now(tz=datetime.UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="test",
        params={
            "test_param": ActionParameter(
                name="test_param", value="string", source_node_id="test_node_id"
            )
        },
        current_node_id="test_node_id",
    )


@pytest.fixture
def json_storage(tmp_path, state):
    print(f"Temp dir: {tmp_path.absolute()}")
    storage = JsonStateStorage(tmp_path)
    storage.save_state(state)
    return storage


@pytest.fixture
def json_storage_upload_workflow(json_storage):
    workflow = json_storage.upload_workflow(Path("../examples/simple_workflow.json"))
    assert workflow is not None
    return json_storage


@pytest.fixture
def add_output(json_storage):
    state = json_storage.load_state()
    assert state is not None
    state.outputs["test_node_id"] = "test_node_id_output"
    json_storage.save_state(state)
    return json_storage


@pytest.fixture
def add_param(json_storage):
    state = json_storage.load_state()
    assert state is not None
    state.params["test_param"] = ActionParameter(
        name="test_param", value="test_param_value", source_node_id="test_node_id"
    )
    json_storage.save_state(state)
    return json_storage


@pytest.fixture
def corrupt_timestamp(tmp_path,json_storage):
    corrupt(tmp_path, "timestamp", "invalid_timestamp")
    return tmp_path


@pytest.fixture
def corrupt_state(tmp_path,json_storage):
    corrupt(tmp_path, "invalid_field", "invalid_value")
    return tmp_path


@pytest.fixture
def not_exist_work_dir(tmp_path,json_storage):
    corrupt(tmp_path, "work_dir", "not_exist_work_dir")
    return tmp_path


@pytest.fixture
def corrupt_json(tmp_path,json_storage):
    state_file = tmp_path.joinpath("state.json")
    with open(state_file, "r") as f:
        data = f.read()
    data = data[:-1]  # Remove the last character to corrupt the JSON
    with open(state_file, "w") as f:
        f.write(data)
    return tmp_path


def test_load_state(json_storage, state):
    loaded_state = json_storage.load_state()
    assert loaded_state == state


def test_save_state(tmp_path, json_storage):
    state_file = tmp_path.joinpath("state.json")
    exist = state_file.is_file()
    print(f" file {state_file.absolute()} exist? {exist}")
    assert exist


def test_load_state_with_corrupt_timestamp(corrupt_timestamp):
    storage = JsonStateStorage(corrupt_timestamp)
    with pytest.raises(StateError) as error:
        storage.load_state()
    assert error.value.args[0] == "Invalid timestamp format"
    print(f" Corrupted timestamp error:  {error.value}, cause: {error.value.__cause__}")


def test_load_corrupt_state(corrupt_state):
    storage = JsonStateStorage(corrupt_state)
    with pytest.raises(StateError) as error:
        storage.load_state()
    assert error.value.args[0] == "Invalid State JSON format"
    print(f" Corrupted state error:  {error.value}, cause: {error.value.__cause__}")


def test_load_corrupt_json(corrupt_json):
    storage = JsonStateStorage(corrupt_json)
    with pytest.raises(StateError) as error:
        storage.load_state()
    assert error.value.args[0] == "Invalid JSON format"
    print(f" Corrupted JSON error:  {error.value}, cause: {error.value.__cause__}")


def test_load_not_exist_work_dir(not_exist_work_dir):
    storage = JsonStateStorage(not_exist_work_dir)
    with pytest.raises(StateError) as error:
        storage.load_state()
    assert error.value.args[0].startswith("Invalid work_dir path")
    print(f" Not exist work_dir:  {error.value}")


def test_add_output(add_output):
    state = add_output.load_state()
    assert state is not None
    assert state.outputs["test_node_id"] == "test_node_id_output"
    print(f" Added output:  {state.outputs}")


def test_add_param(add_param):
    state = add_param.load_state()
    assert state is not None
    assert state.params["test_param"] == ActionParameter(
        name="test_param", value="test_param_value", source_node_id="test_node_id"
    )
    print(f" Added param:  {state.params}")


def corrupt(json_storage, key: str, corrupted_value):
    state_file = json_storage.joinpath("state.json")
    with open(state_file, "r") as f:
        data = json.loads(f.read())
    data[key] = corrupted_value
    with open(state_file, "w") as f:
        f.write(json.dumps(data))
    return json_storage


def test_upload_workflow(json_storage_upload_workflow):
    workflow = json_storage_upload_workflow.load_workflow()
    assert workflow is not None
    assert workflow.flow_id == "simple-workflow"
    assert workflow.nodes[0].id== "NODE_1"
    print(f" Uploaded workflow:  {workflow.flow_id}, nodes: {[node.id for node in workflow.nodes]}")

