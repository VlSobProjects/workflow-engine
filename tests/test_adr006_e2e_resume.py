"""ADR 006 resume equivalence: a paused and resumed run ends where a straight run ends.

The scenario is the one the ADR names as its acceptance case: run the folder scan under a restrictive
`max_nodes_visited`, let the engine stop on the budget, raise the budget as an operator, resume, and
compare the contract surfaces (`state.params` and `state.artifacts`) with a straight run.

Every step after the pause uses a fresh engine, so the resume is proven across engine instances and not
inside one warm object.
"""

import json
from pathlib import Path

from tests.test_adr006_e2e_scan import build_workflow, create_engine, create_scan_fixture
from workflow_engine.models.state import SessionEventCode, StateModel

PAUSE_BUDGET = 5


def prepared_session(work_dir: Path, scan_root: Path) -> str:
    work_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = work_dir / "workflow.json"
    workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))
    return create_engine(work_dir).init_new_session(workflow_path)


def artifact_content(state: StateModel, logical_name: str) -> str:
    artifact = state.artifacts[logical_name]
    return (state.work_dir / "artifacts" / artifact.relative_path).read_text()


def codes(state: StateModel) -> list[str]:
    return [event.code for event in state.session_events]


def run_straight(tmp_path: Path, scan_root: Path) -> StateModel:
    session_id = prepared_session(tmp_path, scan_root)
    response, state = create_engine(tmp_path).start_workflow(session_id)
    assert response.title == "Loop finished"
    return state


def run_paused_then_resumed(tmp_path: Path, scan_root: Path) -> StateModel:
    session_id = prepared_session(tmp_path, scan_root)

    create_engine(tmp_path).set_session_limits(session_id, PAUSE_BUDGET)
    paused_response, paused_state = create_engine(tmp_path).start_workflow(session_id)
    assert paused_response.title == "Workflow budget exceeded"
    assert paused_state.nodes_visited == PAUSE_BUDGET

    # 0 is the unlimited budget, which is the operator raising the limit to "no limit".
    create_engine(tmp_path).set_session_limits(session_id, 0)
    resumed_response, resumed_state = create_engine(tmp_path).start_workflow(session_id)
    assert resumed_response.title == "Loop finished"
    return resumed_state


def test_a_resumed_run_ends_with_the_same_parameters_and_artifacts(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan-root"
    create_scan_fixture(scan_root)

    straight = run_straight(tmp_path / "straight", scan_root)
    resumed = run_paused_then_resumed(tmp_path / "resumed", scan_root)

    assert straight.session_id != resumed.session_id
    assert resumed.nodes_visited > PAUSE_BUDGET

    straight_rows = straight.get_param("table_rows", list)
    resumed_rows = resumed.get_param("table_rows", list)
    assert straight_rows is not None
    assert sorted(resumed_rows, key=lambda row: row["Path"]) == sorted(straight_rows, key=lambda row: row["Path"])

    # `state.params` is a flat namespace keyed by name; key order is not part of the ADR contract and
    # differs after a reload, because the state file is written with sorted keys.
    assert sorted(resumed.params.keys()) == sorted(straight.params.keys())
    assert {name: param.value for name, param in resumed.params.items()} == {
        name: param.value for name, param in straight.params.items()
    }

    assert sorted(resumed.artifacts.keys()) == sorted(straight.artifacts.keys())
    assert resumed.artifacts["file_scan_table"].relative_path == straight.artifacts["file_scan_table"].relative_path
    assert artifact_content(resumed, "file_scan_table") == artifact_content(straight, "file_scan_table")

    assert resumed.artifact_events == []
    assert straight.artifact_events == []


def test_the_journal_tells_the_whole_story_of_a_resumed_run(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan-root"
    create_scan_fixture(scan_root)

    resumed = run_paused_then_resumed(tmp_path / "resumed", scan_root)

    assert codes(resumed) == [
        SessionEventCode.SESSION_CREATED.value,
        SessionEventCode.OPERATOR_LIMIT_UPDATED.value,
        SessionEventCode.WORKFLOW_STARTED.value,
        SessionEventCode.WORKFLOW_PAUSED_LIMIT.value,
        SessionEventCode.OPERATOR_LIMIT_UPDATED.value,
        SessionEventCode.WORKFLOW_RESUMED.value,
        SessionEventCode.WORKFLOW_COMPLETED.value,
    ]

    pause = resumed.session_events[3]
    assert pause.details["nodes_visited"] == PAUSE_BUDGET
    assert pause.details["max_nodes_visited"] == PAUSE_BUDGET

    raise_limit = resumed.session_events[4]
    assert raise_limit.details["limit_before"] == PAUSE_BUDGET
    assert raise_limit.details["limit_after"] == 0
