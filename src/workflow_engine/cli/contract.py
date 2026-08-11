from dataclasses import dataclass, field
from enum import Enum

from workflow_engine.models.state import SessionEventCode, StateReadOnlyView, WorkflowStatusCode


class CommandName(Enum):
    INIT_NEW_SESSION = "init-new-session"
    RUN = "run"
    RESUME = "resume"
    SET_LIMIT = "set-limit"
    SHOW_STATE = "show-state"
    LIST_SESSIONS = "list-sessions"
    HELP_COMPONENTS = "help-components"
    HELP_COMPONENT = "help-component"


class CommandStatus(Enum):
    COMPLETED = "completed"
    ERROR = "error"


INFO_COMMANDS = (
    CommandName.LIST_SESSIONS,
    CommandName.HELP_COMPONENTS,
    CommandName.HELP_COMPONENT,
    CommandName.SHOW_STATE,
    CommandName.SET_LIMIT,
)

# fields: command, session_id, command_status, workflow_status, event_code, message, errors, data;


@dataclass
class CommandResult:
    command: CommandName
    command_status: CommandStatus
    session_id: str | None = field(default=None)
    workflow_status: WorkflowStatusCode | None = field(default=None)
    event_code: SessionEventCode | None = field(default=None)
    message: str | None = field(default=None)
    errors: dict[str, str] | None = field(default=None)
    data: dict[str, object] | None = field(default_factory=dict)

    @classmethod
    def from_state(
        cls, command: CommandName, command_status: CommandStatus, state: StateReadOnlyView, message: str | None = None
    ) -> "CommandResult":
        return cls(
            command=command,
            command_status=command_status,
            workflow_status=state.get_workflow_status_code(),
            event_code=state.get_last_event_code(),
            session_id=state.session_id,
            message=message,
            errors=state.get_errors(),
            data=cls.get_data_from_state(state, full=False),
        )

    @staticmethod
    def get_data_from_state(state: StateReadOnlyView, full: bool) -> dict[str, object]:
        data: dict[str, object] = {
            "timestamp": state.timestamp.isoformat(),
            "flow_id": state.flow_id,
            "schema_version": state.schema_version,
            "work_dir": state.get_work_dir().as_posix(),
            "current_node": state.current_node_id,
            "max_nodes_visited": state.max_nodes_visited,
            "nodes_visited": state.nodes_visited,
        }
        if state.error_code is not None:
            data["error_code"] = state.error_code
        if state.error_msg is not None:
            data["error_message"] = state.error_msg

        if full:
            data.update(
                {
                    "outputs": state.outputs(),
                    "parameters": state.get_parameters(),
                    "artifacts_path": state.get_artifacts_path(),
                    "artifacts": state.get_artifacts(),
                }
            )
        return data

    @classmethod
    def from_state_full(
        cls, command: CommandName, command_status: CommandStatus, state: StateReadOnlyView, message: str | None = None
    ) -> "CommandResult":
        return cls(
            command=command,
            command_status=command_status,
            workflow_status=state.get_workflow_status_code(),
            event_code=state.get_last_event_code(),
            session_id=state.session_id,
            message=message,
            errors=state.get_errors(),
            data=cls.get_data_from_state(state, full=True),
        )
