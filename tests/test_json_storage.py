import json
from datetime import datetime

import pytest

from workflow_engine.exceptions import StateError
from workflow_engine.models.state import StateModel, ActionParameter
from workflow_engine.storage.json_storage import JsonStateStorage


@pytest.fixture
def state(tmp_path):
    return StateModel(
        timestamp=datetime.now(),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="test",
        params={"test_param": ActionParameter(name="test_param", value="string", source_node_id="test_node_id")},
        current_node_id="test_node_id",
    )

@pytest.fixture
def json_storage(tmp_path, state):
    storage = JsonStateStorage(tmp_path)
    storage.save_state(state)
    return tmp_path

@pytest.fixture
def add_output(json_storage):
    storage = JsonStateStorage(json_storage)
    state = storage.load_state()
    assert state is not None
    state.outputs["test_node_id"] = "test_node_id_output"
    storage.save_state(state)
    return json_storage

@pytest.fixture
def add_param(json_storage):
    storage = JsonStateStorage(json_storage)
    state = storage.load_state()
    assert state is not None
    state.params["test_param"] = ActionParameter(name="test_param",value="test_param_value",source_node_id="test_node_id")
    storage.save_state(state)
    return json_storage


@pytest.fixture
def corrupt_timestamp(json_storage):
    corrupt(json_storage,"timestamp","invalid_timestamp")
    return json_storage

@pytest.fixture
def corrupt_state(json_storage):
    corrupt(json_storage,"invalid_field","invalid_value")
    return json_storage

@pytest.fixture
def not_exist_work_dir(json_storage):
    corrupt(json_storage,"work_dir","not_exist_work_dir")
    return json_storage


@pytest.fixture
def corrupt_json(json_storage):
    state_file = json_storage.joinpath("state.json")
    with open(state_file, "r") as f:
        data = f.read()
    data = data[:-1]  # Remove the last character to corrupt the JSON
    with open(state_file, "w") as f:
        f.write(data)
    return json_storage


def test_load_state(json_storage, state):
    storage = JsonStateStorage(json_storage)
    loaded_state = storage.load_state()
    assert loaded_state == state



def test_save_state(json_storage):
    state_file = json_storage.joinpath("state.json")
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
    storage = JsonStateStorage(add_output)
    state = storage.load_state()
    assert state is not None
    assert state.outputs["test_node_id"] == "test_node_id_output"
    print(f" Added output:  {state.outputs}")

def test_add_param(add_param):
    storage = JsonStateStorage(add_param)
    state = storage.load_state()
    assert state is not None
    assert state.params["test_param"] == ActionParameter(name="test_param",value="test_param_value",source_node_id="test_node_id")
    print(f" Added param:  {state.params}")

# def test_upload_workflow(json_storage):
#     storage = JsonStateStorage(json_storage)
#     workflow = storage.upload_workflow(Path(""))

def corrupt(json_storage,key:str, corrupted_value):
    state_file = json_storage.joinpath("state.json")
    data = json.loads(open(state_file).read())
    data[key] = corrupted_value
    with open(state_file, "w") as f:
        f.write(json.dumps(data))
    return json_storage