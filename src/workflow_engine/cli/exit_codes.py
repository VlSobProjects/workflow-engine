from enum import Enum

from workflow_engine.cli.contract import INFO_COMMANDS, CommandName, CommandStatus
from workflow_engine.models.state import WorkflowStatusCode


class ExitCode(Enum):
    COMPLETED = 0
    PAUSED = 2
    FAILED = 3
    ERROR = 4


def get_exit_code(
    command_name: CommandName, command_status: CommandStatus, workflow_status_code: WorkflowStatusCode | None
) -> ExitCode:
    if command_status == CommandStatus.ERROR:
        return ExitCode.ERROR
    if command_name in INFO_COMMANDS:
        return ExitCode.COMPLETED
    elif workflow_status_code == WorkflowStatusCode.PAUSED:
        return ExitCode.PAUSED
    elif workflow_status_code == WorkflowStatusCode.FAILED:
        return ExitCode.FAILED
    else:
        return ExitCode.COMPLETED
