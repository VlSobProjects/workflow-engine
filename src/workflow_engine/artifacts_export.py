from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from workflow_engine.exceptions import ArtifactNotFoundError, WorkflowRuntimeError
from workflow_engine.models.state import ARTIFACTS_DIR, SessionEvent, SessionEventCode, StateModel


@dataclass(frozen=True)
class ExportedArtifact:
    """One deliverable copied out of the session sandbox to the operator destination."""

    logical_name: str
    target_path: str  # absolute POSIX path of the copy


def _copy_artifact_file(artifacts_root: Path, relative_path: Path, destination: Path) -> Path:
    """Copy one artifact preserving its relative path under the destination, overwriting if present.

    The destination is operator-owned, so re-export is idempotent. Parent directories are created
    as needed. See ADR 011.
    """
    source = (artifacts_root / relative_path).resolve()
    target = destination / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target.resolve()


def export_deliverables_on_completion(state: StateModel, deliverables: tuple[str, ...], destination: Path) -> None:
    """Copy each declared deliverable to ``destination`` and record the outcome as engine events.

    Delivery problems never annul the completed work: a deliverable missing from the state records
    ``deliverable_missing``, a failed copy records ``artifact_export_failed``, and the successfully
    exported set records ``artifacts_exported``. All three keep the workflow status ``completed``.
    See ADR 011.
    """
    artifacts_root = state.work_dir / ARTIFACTS_DIR
    exported: dict[str, str] = {}
    for name in deliverables:
        artifact = state.artifacts.get(name)
        if artifact is None:
            state.record_session_event(
                SessionEvent.engine_event(SessionEventCode.DELIVERABLE_MISSING, {"logical_name": name})
            )
            continue
        try:
            target = _copy_artifact_file(artifacts_root, artifact.relative_path, destination)
        except OSError as error:
            state.record_session_event(
                SessionEvent.engine_event(
                    SessionEventCode.ARTIFACT_EXPORT_FAILED, {"logical_name": name, "error": str(error)}
                )
            )
            continue
        exported[name] = target.as_posix()
    if exported:
        state.record_session_event(
            SessionEvent.engine_event(
                SessionEventCode.ARTIFACTS_EXPORTED,
                {"exported": exported, "destination": destination.resolve().as_posix()},
            )
        )


def copy_named_artifacts(state: StateModel, names: tuple[str, ...], destination: Path) -> list[ExportedArtifact]:
    """Copy named registered artifacts to ``destination``; the manual salvage path.

    Unlike the completion export this records no session events: it is operator-invoked retrieval on
    a session that may be paused or failed, and appending export events there would corrupt the
    status derived from the last event. A resolution problem (unknown name, missing file) is raised
    as a WorkflowEngineError so the CLI reports it as an exit-4 error. See ADR 011.
    """
    artifacts_root = state.work_dir / ARTIFACTS_DIR
    exported: list[ExportedArtifact] = []
    for name in names:
        artifact = state.artifacts.get(name)
        if artifact is None:
            raise ArtifactNotFoundError(name=name, message="not registered in this session")
        try:
            target = _copy_artifact_file(artifacts_root, artifact.relative_path, destination)
        except OSError as error:
            raise WorkflowRuntimeError(f"Failed to export artifact '{name}': {error}") from error
        exported.append(ExportedArtifact(logical_name=name, target_path=target.as_posix()))
    return exported
