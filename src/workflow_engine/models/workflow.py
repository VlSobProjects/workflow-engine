from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from workflow_engine.exceptions import WorkflowEngineError
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_with_checker


class WorkflowSource(ABC):
    """Abstract base class for workflow sources."""

    @abstractmethod
    def load_workflow(self, session_id: str) -> WorkflowModel:
        """Load and return a workflow model from storage."""

    @abstractmethod
    def save_workflow(self, session_id, workflow: WorkflowModel) -> None:
        """Save a workflow model to the storage."""

    @staticmethod
    def upload_workflow_from_file(work_flow_file_path: Path) -> WorkflowModel:
        """Upload workflow model from file."""
        try:
            if not work_flow_file_path.exists():
                raise WorkflowEngineError(f"Workflow file not found at path: {work_flow_file_path.absolute()}")
            with work_flow_file_path.open() as f:
                json_obj = json.load(f)
            return WorkflowModel.from_dict(json_obj)
        except FileNotFoundError as ex:
            raise WorkflowEngineError(f"Workflow file not found at path: {work_flow_file_path.absolute()}") from ex
        except json.JSONDecodeError as ex:
            raise WorkflowEngineError(
                f"Invalid JSON format in workflow file at path: {work_flow_file_path.absolute()}"
            ) from ex
        except TypeError as ex:
            raise WorkflowEngineError(
                f"Invalid Workflow JSON format in workflow file at path: {work_flow_file_path.absolute()}"
            ) from ex


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
        nodes = parameter_from_dict_with_checker(
            data=data,
            param_name="nodes",
            expected_type=list,
            checker=lambda x: len(x) > 0,
            fail_message="Nodes must be a not empty list of workflow nodes",
        )
        return cls(
            schema_version=parameter_from_dict(data, "schema_version", str),
            flow_id=parameter_from_dict(data, "flow_id", str),
            start_node_id=parameter_from_dict(data, "start_node_id", str),
            nodes=[WorkflowNodeModel.from_dict(node) for node in nodes if isinstance(node, dict)],
        )
