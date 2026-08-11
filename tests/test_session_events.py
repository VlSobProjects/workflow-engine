"""Session control journal at the engine boundary, as ADR 006 section 10 defines it.

The workflows are built in the temporary directory, so the tests do not depend on files outside the
repository.
"""

import json
from pathlib import Path

import pytest

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.engine import WorkflowEngine
from workflow_engine.models.state import SessionEventCode, StateModel


def create_engine(tmp_path: Path) -> WorkflowEngine:
    return Bootstrap(WorkflowEngineConfiguration(work_dir=tmp_path.as_posix())).build_engine()


def create_folder_node(node_id: str, work_dir: Path, folder_name: str) -> dict[str, object]:
    return {
        "id": node_id,
        "action_type": "function",
        "action_parameters": {
            "function_name": "create_folder",
            "function_parameters": {"path_target": work_dir.as_posix(), "folder_name": folder_name},
        },
    }


def write_workflow(tmp_path: Path, nodes: list[dict[str, object]]) -> Path:
    workflow = {
        "schema_version": "1",
        "flow_id": "journal-flow",
        "start_node_id": nodes[0]["id"],
        "nodes": nodes,
    }
    workflow_file = tmp_path / "source_workflow.json"
    with workflow_file.open("w") as f:
        json.dump(workflow, f)
    return workflow_file


def two_node_workflow(tmp_path: Path) -> Path:
    first = create_folder_node("NODE_1", tmp_path, "first")
    first["transitions"] = [{"next": "NODE_2"}]
    return write_workflow(tmp_path, [first, create_folder_node("NODE_2", tmp_path, "second")])


def codes(state: StateModel) -> list[str]:
    return [event.code.value for event in state.session_events]


def persisted_state(tmp_path: Path, session_id: str) -> StateModel:
    """Read the state back through the storage recorded in the session, without reusing the engine."""
    engine = create_engine(tmp_path)
    session = engine.session_factory.load_session(session_id)
    return engine.storage_factory.build_storage(session.storage).load_state(session_id)


@pytest.fixture
def workflow_file(tmp_path) -> Path:
    return two_node_workflow(tmp_path)


def test_the_first_run_is_started_and_the_next_one_is_resumed(tmp_path, workflow_file):
    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_file)
    _, state = engine.start_workflow(session_id=session_id)

    assert codes(state).count(SessionEventCode.WORKFLOW_STARTED.value) == 1
    assert SessionEventCode.WORKFLOW_RESUMED.value not in codes(state)

    _, state = engine.start_workflow(session_id=session_id)

    assert codes(state).count(SessionEventCode.WORKFLOW_STARTED.value) == 1
    assert codes(state).count(SessionEventCode.WORKFLOW_RESUMED.value) == 1


def test_a_new_engine_resumes_instead_of_starting_the_session_again(tmp_path, workflow_file):
    session_id = create_engine(tmp_path).init_new_session(workflow_file)

    # The first run happens in an engine that never created the session, which is what a restarted
    # process looks like. The journal, not the engine cache, has to decide that this is a start.
    _, state = create_engine(tmp_path).start_workflow(session_id=session_id)
    assert codes(state).count(SessionEventCode.WORKFLOW_STARTED.value) == 1
    assert SessionEventCode.WORKFLOW_RESUMED.value not in codes(state)

    _, state = create_engine(tmp_path).start_workflow(session_id=session_id)
    assert codes(state).count(SessionEventCode.WORKFLOW_STARTED.value) == 1
    assert codes(state).count(SessionEventCode.WORKFLOW_RESUMED.value) == 1


def test_the_run_entry_event_is_persisted_before_the_run(tmp_path, workflow_file):
    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_file)
    engine.start_workflow(session_id=session_id)

    stored = codes(persisted_state(tmp_path, session_id))

    assert stored[0] == SessionEventCode.SESSION_CREATED.value
    assert stored[1] == SessionEventCode.WORKFLOW_STARTED.value


def test_a_completed_run_records_completion(tmp_path, workflow_file):
    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_file)
    response, state = engine.start_workflow(session_id=session_id)

    assert response.title == "Loop finished"
    assert codes(state)[-1] == SessionEventCode.WORKFLOW_COMPLETED.value
    assert codes(persisted_state(tmp_path, session_id))[-1] == SessionEventCode.WORKFLOW_COMPLETED.value


def test_a_failed_node_records_failure(tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["validators"] = [{"function_name": "is_output_exist_file"}]
    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(write_workflow(tmp_path, [node]))
    response, state = engine.start_workflow(session_id=session_id)

    assert response.title == "Node failed"
    assert codes(state)[-1] == SessionEventCode.WORKFLOW_FAILED.value
    assert codes(persisted_state(tmp_path, session_id))[-1] == SessionEventCode.WORKFLOW_FAILED.value


def test_a_setup_failure_is_recorded(tmp_path):
    node = create_folder_node("NODE_1", tmp_path, "made")
    node["transitions"] = [{"next": "MISSING_NODE"}]
    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(write_workflow(tmp_path, [node]))
    response, state = engine.start_workflow(session_id=session_id)

    assert response.title == "Error in workflow setup"
    assert codes(state)[-1] == SessionEventCode.WORKFLOW_SETUP_FAILED.value
    assert codes(persisted_state(tmp_path, session_id))[-1] == SessionEventCode.WORKFLOW_SETUP_FAILED.value
    assert state.session_events[-1].details["node_id"] == "NODE_1"
    assert state.session_events[-1].details["title"] == "Error in workflow setup"


def test_a_run_stopped_by_the_budget_records_the_pause(tmp_path, workflow_file):
    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_file)
    engine.set_session_limits(session_id, 1)
    response, state = engine.start_workflow(session_id=session_id)

    assert response.title == "Workflow budget exceeded"
    assert codes(state)[-1] == SessionEventCode.WORKFLOW_PAUSED_LIMIT.value
    assert codes(persisted_state(tmp_path, session_id))[-1] == SessionEventCode.WORKFLOW_PAUSED_LIMIT.value


def test_updating_the_limit_is_not_a_resume(tmp_path, workflow_file):
    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_file)
    engine.set_session_limits(session_id, 5)

    state = persisted_state(tmp_path, session_id)

    assert codes(state) == [SessionEventCode.SESSION_CREATED.value, SessionEventCode.OPERATOR_LIMIT_UPDATED.value]
    # The old and the new limit are structured fields, so an operator tool does not have to parse prose.
    assert state.session_events[1].details == {"nodes_visited": 0, "limit_before": 0, "limit_after": 5}


def test_updating_the_limit_from_another_engine_is_not_a_resume(tmp_path, workflow_file):
    session_id = create_engine(tmp_path).init_new_session(workflow_file)
    create_engine(tmp_path).set_session_limits(session_id, 5)

    stored = codes(persisted_state(tmp_path, session_id))

    assert SessionEventCode.WORKFLOW_RESUMED.value not in stored
    assert SessionEventCode.WORKFLOW_STARTED.value not in stored
    assert stored[-1] == SessionEventCode.OPERATOR_LIMIT_UPDATED.value


def test_the_engine_never_serves_a_session_with_the_storage_of_another_one(tmp_path, workflow_file):
    """The cached runtime is a cache: another session id must reload session, storage and state together."""
    engine = create_engine(tmp_path)
    first_session = engine.init_new_session(workflow_file)
    engine.start_workflow(session_id=first_session)

    second_session = create_engine(tmp_path).init_new_session(workflow_file)
    engine.set_session_limits(second_session, 7)

    assert engine.session is not None
    assert engine.session.session_id == second_session
    assert persisted_state(tmp_path, second_session).max_nodes_visited == 7
    assert persisted_state(tmp_path, first_session).max_nodes_visited == 0
