import datetime
import json

import pytest

from tests.fixtures.simple_workflow import write_simple_workflow
from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.exceptions import StateLoadError, WorkflowConfigurationError
from workflow_engine.models.state import ActionParameter, StateModel
from workflow_engine.storage.json_storage import JsonStorage

SESSION_ID = "test_session_id"

COMPONENT_REPORT = False


@pytest.fixture
def load_engine(tmp_path):
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=tmp_path.as_posix()))
    engine = bootstrap.build_engine()
    global COMPONENT_REPORT
    if not COMPONENT_REPORT:
        print("\n" + engine.components_report())
        COMPONENT_REPORT = True
    return engine


@pytest.fixture
def state(load_engine, tmp_path):
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
    storage = JsonStorage(tmp_path)
    storage.save_state(state)
    return storage


@pytest.fixture
def json_storage_upload_workflow(json_storage, tmp_path):
    json_storage.save_workflow(
        session_id=SESSION_ID, workflow=json_storage.upload_workflow_from_file(write_simple_workflow(tmp_path))
    )
    workflow = json_storage.load_workflow(session_id=SESSION_ID)
    assert workflow is not None
    return json_storage


@pytest.fixture
def add_output(json_storage):
    state = json_storage.load_state(SESSION_ID)
    assert state is not None
    state.outputs["test_node_id"] = "test_node_id_output"
    json_storage.save_state(state)
    return json_storage


@pytest.fixture
def add_param(json_storage):
    state = json_storage.load_state(SESSION_ID)
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
    state_file = tmp_path.joinpath(json_storage.storage_dir).joinpath(SESSION_ID).joinpath("state.json")
    with state_file.open() as f:
        data = f.read()
    data = data[:-1]  # Remove the last character to corrupt the JSON
    with state_file.open("w") as f:
        f.write(data)
    return tmp_path


def test_load_state(json_storage, state):
    loaded_state = json_storage.load_state(SESSION_ID)
    assert loaded_state == state


def test_save_state_raises_configuration_error_when_storage_dir_cannot_be_created(tmp_path):
    storage_path = tmp_path / "storage"
    storage_path.write_text("not a directory")
    storage = JsonStorage(storage_path)
    state = StateModel(
        timestamp=datetime.datetime.now(tz=datetime.UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="test",
        current_node_id="test_node_id",
        session_id=SESSION_ID,
    )

    with pytest.raises(WorkflowConfigurationError, match="Failed to create storage directory") as error:
        storage.save_state(state)

    assert str(storage_path.resolve(strict=False)) in str(error.value)


def test_save_state(tmp_path, json_storage):
    state_file = tmp_path.joinpath(json_storage.storage_dir).joinpath(SESSION_ID).joinpath("state.json")
    exist = state_file.is_file()
    print(f" file {state_file.absolute()} exist? {exist}")
    assert exist


def test_load_state_with_corrupt_timestamp(corrupt_timestamp):
    storage = JsonStorage(corrupt_timestamp)
    with pytest.raises(StateLoadError, match="Invalid isoformat string") as error:
        storage.load_state(SESSION_ID)
    print(f" Corrupted timestamp error:  {error.value}, cause: {error.value.__cause__}")


def test_load_corrupt_state(corrupt_state):
    storage = JsonStorage(corrupt_state)
    with pytest.raises(StateLoadError, match="Parameter type mismatch") as error:
        storage.load_state(SESSION_ID)
    print(f" Corrupted state error:  {error.value}, cause: {error.value.__cause__}")


def test_load_corrupt_json(corrupt_json):
    storage = JsonStorage(corrupt_json)
    with pytest.raises(StateLoadError, match="Invalid JSON format") as error:
        storage.load_state(SESSION_ID)
    print(f" Corrupted JSON error:  {error.value}, cause: {error.value.__cause__}")


def test_load_not_exist_work_dir(not_exist_work_dir):
    storage = JsonStorage(not_exist_work_dir)
    with pytest.raises(StateLoadError, match="Invalid work_dir path") as error:
        storage.load_state(SESSION_ID)
    print(f" Not exist work_dir:  {error.value}")


def test_add_output(add_output):
    state = add_output.load_state(SESSION_ID)
    assert state is not None
    assert state.outputs["test_node_id"] == "test_node_id_output"
    print(f" Added output:  {state.outputs}")


def test_add_param(add_param):
    state = add_param.load_state(SESSION_ID)
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
    workflow = json_storage_upload_workflow.load_workflow(SESSION_ID)
    assert workflow is not None
    assert workflow.flow_id == "simple-workflow"
    assert workflow.nodes[0].id == "NODE_1"
    print(f" Uploaded workflow:  {workflow.flow_id}, nodes: {[node.id for node in workflow.nodes]}")


def test_workflow_file_with_a_utf8_bom_and_non_ascii_text_is_loaded(tmp_path, json_storage):
    """The definition is an operator-edited file: a BOM and non-ASCII text must survive loading."""
    workflow_path = write_simple_workflow(tmp_path)
    definition = json.loads(workflow_path.read_text(encoding="utf-8"))
    definition["flow_id"] = "naïve-café-workflow"
    workflow_path.write_text(json.dumps(definition, ensure_ascii=False, indent=2), encoding="utf-8-sig")

    workflow = json_storage.upload_workflow_from_file(workflow_path)

    assert workflow.flow_id == "naïve-café-workflow"


def test_state_file_written_as_raw_utf8_keeps_non_ascii_parameter_values(tmp_path, json_storage):
    """A state file is read as UTF-8, not in the platform default encoding."""
    state = json_storage.load_state(SESSION_ID)
    state.params["test_param"] = ActionParameter.create("test_node_id", "test_param", "a résumé of the naïve café")
    json_storage.save_state(state)

    state_file = json_storage.storage_dir / SESSION_ID / "state.json"
    raw = json.loads(state_file.read_text(encoding="utf-8"))
    state_file.write_text(json.dumps(raw, ensure_ascii=False, indent=4), encoding="utf-8")

    assert json_storage.load_state(SESSION_ID).params["test_param"].value == "a résumé of the naïve café"


def test_a_failed_state_write_leaves_the_previous_state_readable(json_storage):
    """Roadmap step 9: the state file is replaced, never rewritten in place.

    The write is made to fail after the file has been opened, which is what a crash mid-write looks
    like from the previous state's side: the session must still be resumable from what was there.
    """
    state = json_storage.load_state(SESSION_ID)
    state.outputs["test_node_id"] = object()  # No encoder handles it, so the write fails while writing.

    with pytest.raises(StateLoadError, match="Failed to save state"):
        json_storage.save_state(state)

    assert json_storage.load_state(SESSION_ID).session_id == SESSION_ID


def test_a_failed_state_write_leaves_no_temporary_file_behind(json_storage):
    state = json_storage.load_state(SESSION_ID)
    state.outputs["test_node_id"] = object()

    with pytest.raises(StateLoadError):
        json_storage.save_state(state)

    assert [entry.name for entry in (json_storage.storage_dir / SESSION_ID).iterdir()] == ["state.json"]


def test_a_completed_state_write_leaves_only_the_state_file(json_storage):
    state = json_storage.load_state(SESSION_ID)
    state.outputs["test_node_id"] = "test_node_id_output"

    json_storage.save_state(state)

    assert [entry.name for entry in (json_storage.storage_dir / SESSION_ID).iterdir()] == ["state.json"]
