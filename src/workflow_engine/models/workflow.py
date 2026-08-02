from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from workflow_engine.models.node import WorkflowNodeModel, decode_string_from_dict


class WorkflowSource(ABC):
    """Abstract base class for workflow sources."""

    @abstractmethod
    def load_workflow(self) -> WorkflowModel:
        """Load and return a workflow model from storage."""

    @staticmethod
    def read_workflow(data: Mapping[str, object]) -> WorkflowModel:
        """Read and return a workflow model from storage."""
        return WorkflowModel.from_dict(data)

    @abstractmethod
    def save_workflow(self, workflow: WorkflowModel) -> None:
        """Save a workflow model to the storage."""

    @abstractmethod
    def upload_workflow(self, work_flow_file_path: Path) -> WorkflowModel:
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

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> WorkflowModel:
        nodes = data.get("nodes")
        if not isinstance(nodes, list) or len(nodes) == 0:
            raise TypeError(f"Nodes must be a not empty list of workflow nodes: {type(nodes).__name__}")
        return cls(
            schema_version=decode_string_from_dict(data, "schema_version"),
            flow_id=decode_string_from_dict(data, "flow_id"),
            start_node_id=decode_string_from_dict(data, "start_node_id"),
            nodes=[WorkflowNodeModel.from_dict(node) for node in nodes if isinstance(node, dict)],
        )
