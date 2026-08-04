import datetime
import importlib
import json

import pytest

from workflow_engine.exceptions import StateLoadError
from workflow_engine.models.state import ActionParameter, StateModel
from workflow_engine.storage.json_storage import JsonStorage

SESSION_ID = "test_session_id"

@pytest.fixture
def load_modules():
    importlib.import_module("workflow_engine.codecs.base_codecs")


@pytest.fixture
def state(load_modules, tmp_path):
    return StateModel(
        timestamp=datetime.datetime.now(tz=datetime.UTC),
        work_dir=tmp_path,
        schema_version="1",
        session_id=SESSION_ID,
        flow_id="test",
        params={"test_param": ActionParameter.create("test_node_id", "test_param", "string")},
        current_node_id="test_node_id",
    )


@pytest.fixture
def json_storage(tmp_path, state):
    print(f"Temp dir: {tmp_path.absolute()}")
    storage = JsonStorage(tmp_path, SESSION_ID)
    storage.save_state(state)
    return storage


@pytest.fixture
def json_storage_upload_workflow(json_storage, examples_dir):
    workflow = json_storage.upload_workflow(examples_dir / "simple_workflow.json")
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
    state.params["test_param"] = ActionParameter.create("test_node_id", "test_param", "test_param_value")
    json_storage.save_state(state)
    return json_storage


@pytest.fixture
def corrupt_timestamp(tmp_path, json_storage):
    corrupt(tmp_path, "timestamp", "invalid_timestamp")
    return tmp_path


@pytest.fixture
def corrupt_state(tmp_path, json_storage):
    corrupt(tmp_path, "timestamp", 10)
    return tmp_path


@pytest.fixture
def not_exist_work_dir(tmp_path, json_storage):
    corrupt(tmp_path, "work_dir", "not_exist_work_dir")
    return tmp_path


@pytest.fixture
def corrupt_json(tmp_path, json_storage):
    state_file = tmp_path.joinpath(json_storage.session_id).joinpath("state.json")
    with state_file.open() as f:
        data = f.read()
    data = data[:-1]  # Remove the last character to corrupt the JSON
    with state_file.open("w") as f:
        f.write(data)
    return tmp_path


def test_load_state(json_storage, state):
    loaded_state = json_storage.load_state()
    assert loaded_state == state


def test_save_state(tmp_path, json_storage):
    state_file = tmp_path.joinpath(json_storage.session_id).joinpath("state.json")
    exist = state_file.is_file()
    print(f" file {state_file.absolute()} exist? {exist}")
    assert exist


def test_load_state_with_corrupt_timestamp(corrupt_timestamp):
    storage = JsonStorage(corrupt_timestamp, SESSION_ID)
    with pytest.raises(StateLoadError, match="Invalid isoformat string") as error:
        storage.load_state()
    print(f" Corrupted timestamp error:  {error.value}, cause: {error.value.__cause__}")


def test_load_corrupt_state(corrupt_state):
    storage = JsonStorage(corrupt_state,SESSION_ID)
    with pytest.raises(StateLoadError, match="Parameter type mismatch") as error:
        storage.load_state()
    print(f" Corrupted state error:  {error.value}, cause: {error.value.__cause__}")


def test_load_corrupt_json(corrupt_json):
    storage = JsonStorage(corrupt_json, SESSION_ID)
    with pytest.raises(StateLoadError,match="Invalid JSON format") as error:
        storage.load_state()
    print(f" Corrupted JSON error:  {error.value}, cause: {error.value.__cause__}")


def test_load_not_exist_work_dir(not_exist_work_dir):
    storage = JsonStorage(not_exist_work_dir, SESSION_ID)
    with pytest.raises(StateLoadError, match="Invalid work_dir path") as error:
        storage.load_state()
    print(f" Not exist work_dir:  {error.value}")


def test_add_output(add_output):
    state = add_output.load_state()
    assert state is not None
    assert state.outputs["test_node_id"] == "test_node_id_output"
    print(f" Added output:  {state.outputs}")


def test_add_param(add_param):
    state = add_param.load_state()
    assert state is not None
    assert state.params["test_param"] == ActionParameter.create(
        name="test_param", value="test_param_value", source_node_id="test_node_id"
    )
    print(f" Added param:  {state.params}")


def corrupt(json_storage, key: str, corrupted_value):
    state_file = json_storage.joinpath(SESSION_ID).joinpath("state.json")
    with state_file.open() as f:
        data = json.loads(f.read())
    data[key] = corrupted_value
    with state_file.open("w") as f:
        f.write(json.dumps(data))
    return json_storage


def test_upload_workflow(json_storage_upload_workflow):
    workflow = json_storage_upload_workflow.load_workflow()
    assert workflow is not None
    assert workflow.flow_id == "simple-workflow"
    assert workflow.nodes[0].id == "NODE_1"
    print(f" Uploaded workflow:  {workflow.flow_id}, nodes: {[node.id for node in workflow.nodes]}")
