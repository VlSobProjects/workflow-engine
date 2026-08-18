import dataclasses
import json
from pathlib import Path

from workflow_engine.exceptions import StateLoadError, WorkflowConfigurationError, WorkflowParameterError
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.models.state import ActionParameter, ArtifactEvent, GuardRecord, SessionEvent, StateModel
from workflow_engine.models.workflow import InputDeclaration, WorkflowModel
from workflow_engine.output import WorkflowArtifact
from workflow_engine.storage.storage import Storage
from workflow_engine.tools import common_encoder

STATE_FILE = "state.json"
WORKFLOW_FILE = "workflow.json"


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

    def load_all_states(self) -> list[StateModel]:
        """Load all states from storage."""
        states = []
        for session_folder in self.storage_dir.iterdir():
            if session_folder.is_dir() and session_folder.joinpath(STATE_FILE).exists():
                state_file = session_folder.joinpath(STATE_FILE)
                try:
                    with state_file.open(encoding="utf-8-sig") as f:
                        json_obj = json.load(f)
                    try:
                        states.append(StateModel.from_dict(json_obj))
                    except WorkflowParameterError as e:
                        print(f"Invalid workflow parameter in state file at path: {state_file.absolute()}: {e}")
                except json.JSONDecodeError as ex:
                    print(f"Invalid JSON format in state file at path: {state_file.absolute()}: {ex}")
        return states

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

    def save_state(self, state: StateModel) -> None:
        """Save state to state file."""
        state_file = self.storage_dir / state.session_id / STATE_FILE
        try:
            self._ensure_storage_directory()
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with state_file.open("w", encoding="utf-8") as f:
                json.dump(state.__dict__, f, indent=4, sort_keys=True, default=state_encoder)
        except WorkflowConfigurationError:
            raise
        except Exception as ex:
            raise StateLoadError(
                "state_file", f"Failed to save state at path: {state_file.resolve(strict=False)}"
            ) from ex
