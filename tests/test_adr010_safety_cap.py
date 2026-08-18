"""The global hard safety cap that bounds every run, as ADR 010 defines it.

A cyclic two-node workflow stands in for an accidental infinite loop: without the hard cap a run
with soft limit 0 would never stop.
"""

import json
from pathlib import Path
from types import MappingProxyType

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.engine import WorkflowEngine
from workflow_engine.models.state import SessionEventCode, StateModel, WorkflowStatusCode


def create_engine(tmp_path: Path, hard_cap: int, storage_dir: Path | None = None) -> WorkflowEngine:
    storage = MappingProxyType({} if storage_dir is None else {"storage_dir": storage_dir.as_posix()})
    config = WorkflowEngineConfiguration(work_dir=tmp_path.as_posix(), storage=storage, hard_max_nodes_visited=hard_cap)
    return Bootstrap(config).build_engine()


def create_folder_node(node_id: str, work_dir: Path, folder_name: str) -> dict[str, object]:
    return {
        "id": node_id,
        "action_type": "function",
        "action_parameters": {
            "function_name": "create_folder",
            "function_parameters": {"path_target": work_dir.as_posix(), "folder_name": folder_name},
        },
    }


def cyclic_workflow(tmp_path: Path) -> Path:
    first = create_folder_node("NODE_1", tmp_path, "first")
    first["transitions"] = [{"next": "NODE_2"}]
    second = create_folder_node("NODE_2", tmp_path, "second")
    second["transitions"] = [{"next": "NODE_1"}]
    workflow = {
        "schema_version": "1",
        "flow_id": "cyclic-flow",
        "start_node_id": "NODE_1",
        "nodes": [first, second],
    }
    workflow_file = tmp_path / "source_workflow.json"
    with workflow_file.open("w") as f:
        json.dump(workflow, f)
    return workflow_file


def codes(state: StateModel) -> list[str]:
    return [event.code.value for event in state.session_events]


def test_a_run_with_no_soft_limit_is_paused_by_the_hard_cap(tmp_path):
    engine = create_engine(tmp_path, hard_cap=3)
    session_id = engine.init_new_session(cyclic_workflow(tmp_path))
    response, state = engine.start_workflow(session_id=session_id)

    assert response.title == "Workflow safety cap reached"
    assert state.nodes_visited == 3
    assert codes(state)[-1] == SessionEventCode.WORKFLOW_PAUSED_SAFETY_LIMIT.value
    assert state.session_events[-1].details == {
        "node_id": "NODE_2",
        "nodes_visited": 3,
        "max_nodes_visited": 0,
        "hard_max_nodes_visited": 3,
    }
    assert state.get_workflow_status_code() == WorkflowStatusCode.PAUSED


def test_the_safety_pause_is_persisted(tmp_path):
    engine = create_engine(tmp_path, hard_cap=3)
    session_id = engine.init_new_session(cyclic_workflow(tmp_path))
    engine.start_workflow(session_id=session_id)

    fresh_engine = create_engine(tmp_path, hard_cap=3)
    session = fresh_engine.session_factory.load_session(session_id)
    stored = fresh_engine.storage_factory.build_storage(session.storage).load_state(session_id)

    assert codes(stored)[-1] == SessionEventCode.WORKFLOW_PAUSED_SAFETY_LIMIT.value


def test_a_lower_soft_limit_still_fires_before_the_hard_cap(tmp_path):
    engine = create_engine(tmp_path, hard_cap=5)
    session_id = engine.init_new_session(cyclic_workflow(tmp_path))
    engine.set_session_limits(session_id, 2)
    response, state = engine.start_workflow(session_id=session_id)

    assert response.title == "Workflow budget exceeded"
    assert state.nodes_visited == 2
    assert codes(state)[-1] == SessionEventCode.WORKFLOW_PAUSED_LIMIT.value


def test_raising_the_soft_limit_does_not_bypass_the_hard_cap(tmp_path):
    engine = create_engine(tmp_path, hard_cap=4)
    session_id = engine.init_new_session(cyclic_workflow(tmp_path))
    engine.set_session_limits(session_id, 50)
    response, state = engine.start_workflow(session_id=session_id)

    assert response.title == "Workflow safety cap reached"
    assert state.nodes_visited == 4
    assert codes(state)[-1] == SessionEventCode.WORKFLOW_PAUSED_SAFETY_LIMIT.value


def test_resume_after_a_config_override_continues_and_ignores_a_storage_change(tmp_path):
    """The override path of ADR 010: the operator raises the cap in the configuration and resumes.

    The edited configuration may also carry a different `storage_dir`; the existing session must keep
    the storage recorded in `session.json` (ADR 004) and the new directory must stay untouched.
    """
    engine = create_engine(tmp_path, hard_cap=3)
    session_id = engine.init_new_session(cyclic_workflow(tmp_path))
    response, state = engine.start_workflow(session_id=session_id)
    assert response.title == "Workflow safety cap reached"
    assert state.nodes_visited == 3

    other_storage = tmp_path / "other-storage"
    raised = create_engine(tmp_path, hard_cap=6, storage_dir=other_storage)
    response, state = raised.start_workflow(session_id=session_id)

    assert codes(state)[-1] == SessionEventCode.WORKFLOW_PAUSED_SAFETY_LIMIT.value
    assert state.nodes_visited == 6
    assert not other_storage.exists()

    session = raised.session_factory.load_session(session_id)
    stored = raised.storage_factory.build_storage(session.storage).load_state(session_id)
    assert stored.nodes_visited == 6
