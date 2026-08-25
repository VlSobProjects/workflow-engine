import json
from pathlib import Path
from types import MappingProxyType

import pytest

from tests.fixtures.simple_workflow import write_simple_workflow
from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.bootstrap.session_factory import SESSION_DIRECTORY, SESSION_FILE
from workflow_engine.bootstrap.storage_factory import JSON_STORAGE_FOLDER_KEY
from workflow_engine.engine import WorkflowEngine
from workflow_engine.exceptions import StateLoadError, WorkflowEngineError

COMPONENT_REPORT = False


def create_engine(tmp_path: Path) -> WorkflowEngine:
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=tmp_path.as_posix()))
    engine = bootstrap.build_engine()
    global COMPONENT_REPORT
    if not COMPONENT_REPORT:
        print("\n" + engine.components_report())
        COMPONENT_REPORT = True
    return engine


def create_engine_with_storage(tmp_path: Path, storage_dir: Path) -> WorkflowEngine:
    """Build an engine whose global configuration points at another storage directory."""
    bootstrap = Bootstrap(
        WorkflowEngineConfiguration(
            work_dir=tmp_path.as_posix(),
            storage=MappingProxyType({JSON_STORAGE_FOLDER_KEY: storage_dir.as_posix()}),
        )
    )
    return bootstrap.build_engine()


def session_file(tmp_path: Path, session_id: str) -> Path:
    return tmp_path / SESSION_DIRECTORY / session_id / SESSION_FILE


def started_session(tmp_path: Path) -> str:
    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_path=write_simple_workflow(tmp_path))
    engine.start_workflow(session_id=session_id)
    return session_id


@pytest.fixture
def load_engine(tmp_path):
    return create_engine(tmp_path)


def test_simple_workflow(load_engine, tmp_path):
    engine = load_engine
    workflow_path = write_simple_workflow(tmp_path)
    session_id = engine.init_new_session(workflow_path=workflow_path)
    _, state = engine.start_workflow(session_id=session_id)

    assert state

    session_file_path = state.work_dir / SESSION_FILE
    assert session_file_path.is_file()

    session = engine.session_factory.load_session(session_id)

    assert session.is_same(state)

    assert state.visit_counters["NODE_3"] == 1
    assert state.visit_counters["NODE_1"] == 1

    with pytest.raises(WorkflowEngineError):
        engine.init_new_session(workflow_path=workflow_path)

    with pytest.raises(WorkflowEngineError):
        engine.start_workflow(session_id="122334")


def test_resume_uses_the_storage_of_the_session_not_the_current_configuration(tmp_path):
    """The point of ADR 004: storage settings of a session survive a change of the global configuration."""
    session_id = started_session(tmp_path)
    recorded_storage = create_engine(tmp_path).session_factory.load_session(session_id).storage

    drifted_storage_dir = tmp_path / "another-storage"
    engine = create_engine_with_storage(tmp_path, drifted_storage_dir)
    response, state = engine.start_workflow(session_id=session_id)

    assert state
    assert state.session_id == session_id
    assert engine.session is not None
    assert engine.session.storage[JSON_STORAGE_FOLDER_KEY] == recorded_storage[JSON_STORAGE_FOLDER_KEY]
    assert not drifted_storage_dir.exists()
    print(f"Resumed under drifted configuration: {response.title}")


def test_the_session_record_is_written_once_and_never_rewritten(tmp_path):
    session_id = started_session(tmp_path)
    record_after_start = session_file(tmp_path, session_id).read_bytes()

    create_engine(tmp_path).start_workflow(session_id=session_id)

    assert session_file(tmp_path, session_id).read_bytes() == record_after_start


def test_resume_fails_when_the_session_record_is_missing(tmp_path):
    session_id = started_session(tmp_path)
    session_file(tmp_path, session_id).unlink()

    with pytest.raises(WorkflowEngineError) as error:
        create_engine(tmp_path).start_workflow(session_id=session_id)

    assert session_id in str(error.value)
    print(f"Missing session record: {error.value}")


def test_resume_fails_explicitly_when_the_session_record_is_corrupted(tmp_path):
    session_id = started_session(tmp_path)
    record = session_file(tmp_path, session_id)
    record.write_text(record.read_text()[:-3])

    # A broken record must arrive as an engine error, not as a raw json decoding failure. See ADR 001.
    with pytest.raises(WorkflowEngineError) as error:
        create_engine(tmp_path).start_workflow(session_id=session_id)

    assert session_id in str(error.value)
    print(f"Corrupted session record: {error.value}")


def test_resume_fails_when_the_session_record_carries_another_session_id(tmp_path):
    session_id = started_session(tmp_path)
    record = session_file(tmp_path, session_id)
    data = json.loads(record.read_text())
    data["session_id"] = "another-session-id"
    record.write_text(json.dumps(data))

    with pytest.raises(WorkflowEngineError) as error:
        create_engine(tmp_path).start_workflow(session_id=session_id)

    # The mismatch has to be reported before the state is looked up, so that the failure names both
    # identifiers instead of a missing state file under a foreign path.
    assert not isinstance(error.value, StateLoadError)
    assert session_id in str(error.value)
    assert "another-session-id" in str(error.value)
    print(f"Session record with a foreign session id: {error.value}")
