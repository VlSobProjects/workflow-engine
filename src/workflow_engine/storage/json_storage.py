import dataclasses
import json
import os
import tempfile
from collections import deque
from pathlib import Path

from workflow_engine.exceptions import StateLoadError, WorkflowConfigurationError
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.models.node_record import NodeRecord, RecordPage
from workflow_engine.models.state import ActionParameter, ArtifactEvent, GuardRecord, SessionEvent, StateModel
from workflow_engine.models.workflow import InputDeclaration, WorkflowModel
from workflow_engine.output import WorkflowArtifact
from workflow_engine.storage.storage import Storage
from workflow_engine.tools import common_encoder

STATE_FILE = "state.json"
WORKFLOW_FILE = "workflow.json"
RECORDS_FILE = "records.jsonl"


def workflow_encoder(obj):
    if isinstance(obj, WorkflowNodeModel):
        return {**dataclasses.asdict(obj)}
    if isinstance(obj, InputDeclaration):
        return obj.to_dict()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def state_encoder(obj):

    obj_common = common_encoder(obj)

    if obj_common is not None:
        return obj_common

    if isinstance(obj, WorkflowArtifact):
        return obj.to_dict()

    if isinstance(obj, SessionEvent):
        return obj.to_dict()

    if isinstance(obj, ArtifactEvent):
        return obj.to_dict()

    if isinstance(obj, ActionParameter):
        return obj.to_dict()

    if isinstance(obj, GuardRecord):
        return obj.to_dict()

    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def write_json_atomically(target: Path, payload: object, encoder) -> None:
    """Write the payload beside the target and replace the target with it in one step.

    The state file is rewritten on every turn, and a write interrupted in place leaves a truncated
    file that no resume can read. The previous file therefore stays untouched until the new content
    is complete on disk: the temporary file lives in the target's own directory, so the replace is a
    rename within one filesystem, and a failed write takes the temporary file with it.
    """
    descriptor, temp_name = tempfile.mkstemp(dir=target.parent, prefix=f"{target.name}.", suffix=".tmp")
    temp_file = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, sort_keys=True, default=encoder)
            f.flush()
            os.fsync(f.fileno())
        temp_file.replace(target)
    except BaseException:
        temp_file.unlink(missing_ok=True)
        raise


class JsonStorage(Storage):
    """JSON Storage class for states and workflows."""

    storage_dir: Path

    def _ensure_storage_directory(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as ex:
            raise WorkflowConfigurationError(
                f"Failed to create storage directory: {self.storage_dir.resolve(strict=False)}"
            ) from ex

    def __init__(self, storage_dir: Path) -> None:
        path = storage_dir.expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        self.storage_dir = path.resolve(strict=False)

    def load_workflow(self, session_id) -> WorkflowModel:
        return self.upload_workflow_from_file(self.storage_dir.joinpath(session_id).joinpath(WORKFLOW_FILE))

    def save_workflow(self, session_id: str, workflow: WorkflowModel) -> None:
        try:
            self._ensure_storage_directory()
            workflow_file = self.storage_dir / session_id / WORKFLOW_FILE
            workflow_file.parent.mkdir(parents=True, exist_ok=True)
            with workflow_file.open("w", encoding="utf-8") as f:
                json.dump(workflow.__dict__, f, indent=4, default=workflow_encoder)
        except WorkflowConfigurationError:
            raise
        except Exception as ex:
            raise WorkflowConfigurationError(
                f"Failed to save workflow to: {self.storage_dir.resolve(strict=False)}"
            ) from ex

    def load_state(self, session_id: str) -> StateModel:
        state_file = self.storage_dir / session_id / STATE_FILE
        try:
            if not state_file.is_file():
                raise StateLoadError("state_file", f"State file not found at path: {state_file.absolute()}")
            with state_file.open(encoding="utf-8-sig") as f:
                json_obj = json.load(f)
            return StateModel.from_dict(json_obj)
        except FileNotFoundError as ex:
            raise StateLoadError("state_file", f"State file not found at path: {state_file.absolute()}") from ex
        except json.JSONDecodeError as ex:
            raise StateLoadError(
                "state_file", f"Invalid JSON format in state file at path: {state_file.absolute()}"
            ) from ex

    def _records_file(self, session_id: str) -> Path:
        return self.storage_dir / session_id / RECORDS_FILE

    def append_record(self, session_id: str, record: NodeRecord) -> None:
        """Append one record as a line of its own, so the trail is only ever added to.

        One line is one record: a write that fails leaves the records before it intact, and no
        record already written is touched. That is what makes the stream evidence. See ADR 021 §2.
        """
        records_file = self._records_file(session_id)
        try:
            self._ensure_storage_directory()
            records_file.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(record.to_dict(), sort_keys=True)
            with records_file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except WorkflowConfigurationError:
            raise
        except Exception as ex:
            raise StateLoadError(
                "records_file", f"Failed to append a node record at path: {records_file.resolve(strict=False)}"
            ) from ex

    def load_records(self, session_id: str, node_id: str | None = None, tail: int | None = None) -> RecordPage:
        """Read the stream line by line, filtering by node first and keeping the last `tail` last.

        A session whose run has written nothing yet has no stream, which is an empty page and not an
        error. A line that does not parse is: the trail is append-only, so a broken line means a
        damaged file, and reporting it as a shorter history would hide the damage. See ADR 021 §4.
        """
        records_file = self._records_file(session_id)
        if not records_file.is_file():
            return RecordPage(records=[], total=0)
        selected: deque[NodeRecord] | list[NodeRecord] = deque(maxlen=tail) if tail is not None else []
        total = 0
        try:
            with records_file.open(encoding="utf-8-sig") as f:
                for number, line in enumerate(f, start=1):
                    if not line.strip():
                        continue
                    total += 1
                    try:
                        record = NodeRecord.from_dict(json.loads(line))
                    except json.JSONDecodeError as ex:
                        raise StateLoadError(
                            "records_file",
                            f"Invalid JSON format in node record file at line {number}: {records_file.absolute()}",
                        ) from ex
                    if node_id is not None and record.node_id != node_id:
                        continue
                    selected.append(record)
        except StateLoadError:
            raise
        except OSError as ex:
            raise StateLoadError(
                "records_file", f"Failed to read node records at path: {records_file.absolute()}"
            ) from ex
        return RecordPage(records=list(selected), total=total)

    def save_state(self, state: StateModel) -> None:
        """Save state to state file."""
        state_file = self.storage_dir / state.session_id / STATE_FILE
        try:
            self._ensure_storage_directory()
            state_file.parent.mkdir(parents=True, exist_ok=True)
            write_json_atomically(state_file, state.__dict__, state_encoder)
        except WorkflowConfigurationError:
            raise
        except Exception as ex:
            raise StateLoadError(
                "state_file", f"Failed to save state at path: {state_file.resolve(strict=False)}"
            ) from ex
