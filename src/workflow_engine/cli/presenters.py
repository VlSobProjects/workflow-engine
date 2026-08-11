from datetime import datetime
from enum import Enum

from workflow_engine.cli.contract import CommandResult, CommandName, CommandStatus
import json

from workflow_engine.models.state import SessionEventCode, WorkflowStatusCode
from workflow_engine.tools import common_encoder

def command_result_encoder(obj):
    obj_common = common_encoder(obj)

    if obj_common is not None:
        return obj_common

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def render_text(response: CommandResult)->str:
    resp_list = [f"Command: {response.command.value}", f"Status: {response.status.value}"]
    if response.workflow_status:
        resp_list.append(f"Workflow Status: {response.workflow_status.value}")
    if response.errors:
        resp_list.append(f"Errors: {response.errors}")
    if response.message:
        resp_list.append(f"Message: {response.message}")
    if response.data:
        resp_list.append(f"Data: {response.data}")
    return "\n".join(resp_list)

def render_json(response: CommandResult)->str:
    return json.dumps(response.__dict__, indent=2, sort_keys=True, default=command_result_encoder)