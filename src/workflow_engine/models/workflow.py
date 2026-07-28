from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from workflow_engine.models.node import WorkflowNodeModel


class WorkflowSource(ABC):
    """Abstract base class for workflow sources."""
    @abstractmethod
    def load_workflow(self) -> WorkflowModel:
        """Load and return a workflow model from storage."""

    @abstractmethod
    def save_workflow(self, workflow: WorkflowModel) -> None:
        """Save a workflow model to the storage."""

    @abstractmethod
    def upload_workflow(self, work_flow_file_path:Path) -> WorkflowModel:
        """Upload and return workflow model to the storage."""


@dataclass(frozen=True)
class WorkflowModel:
    schema_version: str
    flow_id: str
    start_node_id: str
    nodes: list[WorkflowNodeModel]

    def get_node(self, node_id: str) -> WorkflowNodeModel | None:
        """Return the node with the given id, or None if not found."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None