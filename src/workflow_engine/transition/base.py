"""Transition targets and the transition itself.

A transition is a guard and a target. A target is a node, the end of the workflow, or failure of the
node. Targets are static, so the whole graph is known before execution. See ADR 002.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from workflow_engine.exceptions import WorkflowError
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.transition.guards import BaseGuard, GuardRecord


@dataclass(frozen=True)
class Target:
    """Where a node goes when a transition is taken."""

    def is_routing(self) -> bool:
        return False

    def check_error(self, workflow_nodes: set[str]) -> None:
        """Raise when the target cannot be resolved against the workflow. Static targets cannot."""
        return


@dataclass(frozen=True)
class NodeTarget(Target):
    node_id: str

    def is_routing(self) -> bool:
        return True

    def check_error(self, workflow_nodes: set[str]) -> None:
        if self.node_id not in workflow_nodes:
            raise WorkflowError(f"Next node '{self.node_id}' not found in workflow nodes")


@dataclass(frozen=True)
class EndTarget(Target):
    """End the workflow without an error."""


@dataclass(frozen=True)
class FailTarget(Target):
    """Fail the node. A code of None keeps the error code the action already produced."""

    code: str | None = None


@dataclass
class Transition:
    target: Target
    guard: BaseGuard | None = field(default=None)
    attempts: bool = field(default=False)

    def is_routing(self) -> bool:
        return self.target.is_routing()

    def check_error(self, workflow_nodes: set[str]) -> None:
        self.target.check_error(workflow_nodes)

    def matches(self, output: ActionNodeOutput, state: StateModel, trace: list[GuardRecord] | None = None) -> bool:
        if self.guard is None:
            return True
        return self.guard.check(output, state, trace)
