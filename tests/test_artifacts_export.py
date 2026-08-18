"""ADR 011 increment 2: deliverables declaration and engine export on completion."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from tests.test_adr009_e2e_copy_tree import build_workflow, create_source_tree
from workflow_engine.artifacts_export import export_deliverables_on_completion
from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.models.state import SessionEvent, SessionEventCode, StateModel, WorkflowStatusCode
from workflow_engine.models.workflow import WorkflowModel
from workflow_engine.output import WorkflowArtifact


def _base_workflow() -> dict[str, object]:
    return {
        "schema_version": "1",
        "flow_id": "f",
        "start_node_id": "N",
        "nodes": [{"id": "N", "action_type": "stop", "action_parameters": {}}],
    }


def _state(tmp_path: Path, artifacts: dict[str, WorkflowArtifact]) -> StateModel:
    state = StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="f",
        session_id="s",
        current_node_id="N",
        artifacts=artifacts,
    )
    state.record_session_event(SessionEvent.engine_event(SessionEventCode.WORKFLOW_COMPLETED))
    return state


def test_deliverables_absent_is_empty_tuple():
    assert WorkflowModel.from_dict(_base_workflow()).deliverables == ()


def test_deliverables_valid_list_is_kept_in_order():
    workflow = WorkflowModel.from_dict({**_base_workflow(), "deliverables": ["report", "summary"]})
    assert workflow.deliverables == ("report", "summary")


def test_deliverables_non_list_is_rejected():
    with pytest.raises(WorkflowConfigurationError):
        WorkflowModel.from_dict({**_base_workflow(), "deliverables": "report"})


def test_deliverables_duplicate_is_rejected():
    with pytest.raises(WorkflowConfigurationError):
        WorkflowModel.from_dict({**_base_workflow(), "deliverables": ["report", "report"]})


def test_deliverables_empty_entry_is_rejected():
    with pytest.raises(WorkflowConfigurationError):
        WorkflowModel.from_dict({**_base_workflow(), "deliverables": ["report", "  "]})


def test_export_copies_deliverable_preserving_relative_path(tmp_path):
    (tmp_path / "artifacts" / "reports").mkdir(parents=True)
    (tmp_path / "artifacts" / "reports" / "report.csv").write_text("a,b\n1,2\n")
    state = _state(
        tmp_path,
        {"report": WorkflowArtifact(Path("reports/report.csv"), datetime.now(tz=UTC), "the report")},
    )
    destination = tmp_path / "operator"

    export_deliverables_on_completion(state, ("report",), destination)

    assert (destination / "reports" / "report.csv").read_text() == "a,b\n1,2\n"
    last = state.session_events[-1]
    assert last.code == SessionEventCode.ARTIFACTS_EXPORTED
    assert "report" in last.details["exported"]
    assert state.get_workflow_status_code() == WorkflowStatusCode.COMPLETED


def test_export_missing_deliverable_records_event_and_stays_completed(tmp_path):
    state = _state(tmp_path, {})

    export_deliverables_on_completion(state, ("report",), tmp_path / "operator")

    codes = [event.code for event in state.session_events]
    assert SessionEventCode.DELIVERABLE_MISSING in codes
    assert SessionEventCode.ARTIFACTS_EXPORTED not in codes
    assert state.get_workflow_status_code() == WorkflowStatusCode.COMPLETED


def test_export_failed_copy_records_event_and_stays_completed(tmp_path):
    state = _state(
        tmp_path,
        {"report": WorkflowArtifact(Path("reports/absent.csv"), datetime.now(tz=UTC), "never written")},
    )

    export_deliverables_on_completion(state, ("report",), tmp_path / "operator")

    codes = [event.code for event in state.session_events]
    assert SessionEventCode.ARTIFACT_EXPORT_FAILED in codes
    assert state.get_workflow_status_code() == WorkflowStatusCode.COMPLETED


def test_engine_exports_declared_deliverable_on_completion(tmp_path):
    source_root = tmp_path / "source-root"
    create_source_tree(source_root)
    target_dir = tmp_path / "copy-target"
    target_dir.mkdir()
    workflow = build_workflow(source_root, target_dir)
    workflow["deliverables"] = ["copy_report"]
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow, indent=2))
    operator_dir = tmp_path / "operator-out"

    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_path)
    _, state = engine.start_workflow(session_id, export_dir=operator_dir.as_posix())

    assert (operator_dir / "reports" / "copy_report.csv").is_file()
    assert state.session_events[-1].code == SessionEventCode.ARTIFACTS_EXPORTED


def test_engine_does_not_export_without_destination(tmp_path):
    source_root = tmp_path / "source-root"
    create_source_tree(source_root)
    target_dir = tmp_path / "copy-target"
    target_dir.mkdir()
    workflow = build_workflow(source_root, target_dir)
    workflow["deliverables"] = ["copy_report"]
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow, indent=2))

    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_path)
    _, state = engine.start_workflow(session_id)

    codes = [event.code for event in state.session_events]
    assert SessionEventCode.ARTIFACTS_EXPORTED not in codes
    assert state.session_events[-1].code == SessionEventCode.WORKFLOW_COMPLETED
