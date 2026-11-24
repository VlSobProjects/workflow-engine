from dataclasses import dataclass, field

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.registry.action_registry import create_action
from workflow_engine.transition.base import FailTarget, Transition
from workflow_engine.transition.guards import AllOfGuard, NoErrorGuard, negated_guard
from workflow_engine.transition.node_transition import transition_factory


@dataclass
class WorkflowNode:
    id: str
    config: WorkflowNodeModel
    action: BaseAction
    transitions: list[Transition]
    override_parameters: bool = field(default=False)
    set_parameters: dict[str, object] | None = field(default=None)

    def has_routing(self) -> bool:
        return any(transition.is_routing() for transition in self.transitions)


def _post_condition(validator_data: dict[str, object], index: int) -> Transition:
    """Expand a node level validator into the transition that fails the node.

    The transition is taken when the check does not hold, and only when the action produced no error
    code of its own, so that a post-condition never replaces the real cause of a failure.
    """
    guard, name = negated_guard(validator_data)
    return Transition(
        target=FailTarget(code=name),
        guard=AllOfGuard(guards=[NoErrorGuard(), guard]),
        origin=f"validators[{index}]",
    )


def build_transitions(node_model: WorkflowNodeModel) -> list[Transition]:
    """The effective transitions of a node in order: its validators expanded first, then its own."""
    transitions = [_post_condition(validator, index) for index, validator in enumerate(node_model.validators or [])]
    transitions += [
        transition_factory(transition, f"transitions[{index}]")
        for index, transition in enumerate(node_model.transitions or [])
    ]
    return transitions


def workflow_node_factory(node_model: WorkflowNodeModel) -> WorkflowNode:
    action = create_action(node_model.action_type, node_model.action_parameters)
    return WorkflowNode(id=node_model.id, config=node_model, action=action, transitions=build_transitions(node_model))
