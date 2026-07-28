import dataclasses
import json
from datetime import datetime
from pathlib import Path

from workflow_engine.exceptions import StateError, WorkflowError
from workflow_engine.models.state import ActionParameter, StateModel, StateSource
from workflow_engine.models.workflow import WorkflowModel, WorkflowSource

STATE_FILE = "state.json"
WORKFLOW_FILE = "workflow.json"

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# def state_decoder(obj):
#     match obj.get("__type__"):
#         case "datetime":
#             return datetime.fromisoformat(obj["value"])
#         case "ActionParameter":
#             return ActionParameter(**{
#                 k: v for k, v in obj.items() if k != "__type__"
#             })
#     return obj


def state_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, ActionParameter):
        return {**dataclasses.asdict(obj)}

    if isinstance(obj, Path):
        return str(obj)

    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def state_fields_decoder(dct):
    """Decode specific filed and rise SateError exception if not possible"""
    for key, value in dct.items():
        if key == "timestamp":
            try:
                dct[key] = datetime.fromisoformat(value)
            except ValueError as ex:
                raise StateError("Invalid timestamp format") from ex
        if key == "work_dir":
            if not isinstance(value, str):
                raise StateError("Invalid work_dir format")
            elif not Path(value).is_dir():
                raise StateError(f"Invalid work_dir path: {value}")
            else:
                dct[key] = Path(value).absolute()
        if key == "params":
            if not isinstance(value, dict):
                raise StateError("Invalid params format")
            for param_key, param_value in value.items():
                if not isinstance(param_value, dict):
                    raise StateError(f"Invalid param format for key: {param_key}: {param_value}")
                value[param_key] = ActionParameter(**param_value)
    return dct

def workflow_fields_decoder(dct):
    """Decode specific filed and rise WorkflowError exception if not possible"""


def _load_workflow_from_path(work_flow_file_path: Path) -> WorkflowModel:
    try:
        if not work_flow_file_path.exists():
            raise WorkflowError(f"Workflow file not found path: {work_flow_file_path.absolute()}")
        with open(work_flow_file_path) as f:
            json_obj = json.load(f, object_hook=workflow_fields_decoder)
        return WorkflowModel(**json_obj)
    except FileNotFoundError as ex:
        raise WorkflowError("Workflow file not found path:") from ex
    except json.JSONDecodeError as ex:
        raise WorkflowError("Invalid JSON format") from ex
    except TypeError as ex:
        raise WorkflowError("Invalid Workflow JSON format") from ex


class JsonStateStorage(StateSource,WorkflowSource):
    """JSON Storage class for states and workflows."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def upload_workflow(self, work_flow_file_path: Path) -> WorkflowModel:
        workflow = _load_workflow_from_path(work_flow_file_path)
        self.save_workflow(workflow)
        return self.load_workflow()

    def load_workflow(self) -> WorkflowModel:
        return _load_workflow_from_path(self.path.joinpath(WORKFLOW_FILE))

    def save_workflow(self, workflow: WorkflowModel) -> None:
        try:
            workflow_file = self.path.joinpath(WORKFLOW_FILE)
            workflow_file.parent.mkdir(parents=True, exist_ok=True)
            with open(workflow_file, "w") as f:
                json.dump(workflow.__dict__, f, indent=4, sort_keys=True, default=DateTimeEncoder().default)
        except Exception as ex:
            raise WorkflowError("Failed to save workflow") from ex

    def load_state(self) -> StateModel | None:
        try:
            state_file = self.path.joinpath(STATE_FILE)
            if not state_file.is_file():
                raise StateError(f"State file not found path: {state_file}")
            with open(state_file) as f:
                json_obj = json.load(f, object_hook=state_fields_decoder)
            return StateModel(**json_obj)
        except FileNotFoundError as ex:
            raise StateError("State file not found") from ex
        except json.JSONDecodeError as ex:
            raise StateError("Invalid JSON format") from ex
        except TypeError as ex:
            raise StateError("Invalid State JSON format") from ex

    def save_state(self, state: StateModel) -> None:
        """Save state to state file."""
        try:
            state_file = self.path.joinpath(STATE_FILE)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state.__dict__, f, indent=4, sort_keys=True, default=state_encoder)
        except Exception as ex:
            raise StateError("Failed to save state") from ex

