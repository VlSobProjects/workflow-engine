import dataclasses
import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from workflow_engine.exceptions import StateLoadError, WorkflowEngineError
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.models.state import ActionParameter, GuardRecord, StateModel
from workflow_engine.models.workflow import WorkflowModel
from workflow_engine.storage.storage import Storage

STATE_FILE = "state.json"
WORKFLOW_FILE = "workflow.json"


def workflow_encoder(obj):
    if isinstance(obj, WorkflowNodeModel):
        return {**dataclasses.asdict(obj)}
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def state_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, ActionParameter):
        return obj.to_dict()

    if isinstance(obj, GuardRecord):
        return obj.to_dict()

    if isinstance(obj, Path):
        return str(obj)

    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _load_workflow_from_path(work_flow_file_path: Path) -> Mapping[str, object]:
    try:
        if not work_flow_file_path.exists():
            raise WorkflowEngineError(f"Workflow file not found at path: {work_flow_file_path.absolute()}")
        with work_flow_file_path.open() as f:
            json_obj = json.load(f)
        return json_obj
    except FileNotFoundError as ex:
        raise WorkflowEngineError(
            f"Workflow file not found at path: {work_flow_file_path.absolute()}"
        ) from ex
    except json.JSONDecodeError as ex:
        raise WorkflowEngineError(
            f"Invalid JSON format in workflow file at path: {work_flow_file_path.absolute()}"
        ) from ex
    except TypeError as ex:
        raise WorkflowEngineError(
            f"Invalid Workflow JSON format in workflow file at path: {work_flow_file_path.absolute()}"
        ) from ex


class JsonStorage(Storage):
    """JSON Storage class for states and workflows."""


    def __init__(self, working_dir: Path,session_id:str) -> None:
        super().__init__(session_id)
        self.session_working_dir = working_dir / session_id

    def load_workflow(self) -> WorkflowModel:
        return self.read_workflow(_load_workflow_from_path(self.session_working_dir.joinpath(WORKFLOW_FILE)))

    def upload_workflow(self, work_flow_file_path: Path) -> WorkflowModel:
        workflow = self.read_workflow(_load_workflow_from_path(work_flow_file_path))
        self.save_workflow(workflow)
        return self.load_workflow()

    def save_workflow(self, workflow: WorkflowModel) -> None:
        try:
            workflow_file = self.session_working_dir.joinpath(WORKFLOW_FILE)
            workflow_file.parent.mkdir(parents=True, exist_ok=True)
            with workflow_file.open("w") as f:
                json.dump(workflow.__dict__, f, indent=4, default=workflow_encoder)
        except Exception as ex:
            raise WorkflowEngineError("Failed to save workflow") from ex

    def load_state(self) -> StateModel:
        state_file = self.session_working_dir.joinpath(STATE_FILE)
        try:
            if not state_file.is_file():
                raise StateLoadError(
                    "state_file", f"State file not found at path: {state_file.absolute()}"
                )
            with state_file.open() as f:
                json_obj = json.load(f)
            return StateModel.from_dict(json_obj)
        except FileNotFoundError as ex:
            raise StateLoadError(
                "state_file", f"State file not found at path: {state_file.absolute()}"
            ) from ex
        except json.JSONDecodeError as ex:
            raise StateLoadError(
                "state_file",
                f"Invalid JSON format in state file at path: {state_file.absolute()}"
            ) from ex

    def save_state(self, state: StateModel) -> None:
        """Save state to state file."""
        state_file = self.session_working_dir.joinpath(STATE_FILE)
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with state_file.open("w") as f:
                json.dump(state.__dict__, f, indent=4, sort_keys=True, default=state_encoder)
        except Exception as ex:
            raise StateLoadError(
                "state_file", f"Failed to save state at path: {state_file.absolute()}"
            ) from ex
