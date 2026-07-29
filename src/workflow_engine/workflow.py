from dataclasses import dataclass

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.registry.action_registry import create_action
from workflow_engine.transition.base import BaseTransaction
from workflow_engine.validators.output_validators import (
    BaseOutputValidator,
    validator_factory,
)


@dataclass
class WorkflowNode:
    id: str
    config: WorkflowNodeModel
    action: BaseAction
    validators: list[BaseOutputValidator] | None
    transitions: list[BaseTransaction] | None


def workflow_node_factory(node_model: WorkflowNodeModel) -> WorkflowNode:
    from workflow_engine.transition.node_transition import transition_factory

    action = create_action(node_model.action_type, node_model.action_parameters)
    validators = [validator_factory(node) for node in node_model.validators] if node_model.validators else None
    transitions = [transition_factory(node) for node in node_model.transitions] if node_model.transitions else None
    return WorkflowNode(
        id=node_model.id,
        config=node_model,
        action=action,
        validators=validators,
        transitions=transitions
    )


def stop_on_error_node_factory(error:str):
    params = {"error": error}
    from workflow_engine.actions.actions import StopOnError
    action  = StopOnError.from_dict(params)
    return WorkflowNode(
        id='STOP_ON_ERROR',
        config=WorkflowNodeModel(action.ACTION_TYPE.upper(), action.ACTION_TYPE,params),
        action=action,
        validators=None,
        transitions=None
    )