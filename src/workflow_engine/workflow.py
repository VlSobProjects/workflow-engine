from dataclasses import dataclass

from workflow_engine.actions.actions import StopOnError
from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.transition.base import BaseTransaction
from workflow_engine.validators.output_validators import BaseOutputValidator


@dataclass
class WorkflowNode:
    id: str
    config: WorkflowNodeModel
    action: BaseAction
    validator: BaseOutputValidator | None
    transition: list[BaseTransaction] | None


def stop_on_error_node_factory(error:str):
    params = {"error": error}
    action  = StopOnError.from_dict(params)
    return WorkflowNode(
        id='STOP_ON_ERROR',
        config=WorkflowNodeModel(action.ACTION_TYPE.upper(), action.ACTION_TYPE,params),
        action=action,
        validator=None,
        transition=None
    )