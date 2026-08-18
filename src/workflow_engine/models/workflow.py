from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from workflow_engine.exceptions import WorkflowConfigurationError, WorkflowEngineError
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.registry.type_registry import resolve_codec_by_type_name
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_with_checker

_INPUT_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class InputDeclaration:
    """One declared workflow input: the mirror of a deliverable on the input side. See ADR 012.

    ``type`` is the resolved full codec name (``pathlib.Path``) or ``None`` for a plain string input.
    """

    name: str
    type: str | None = None
    required: bool = True
    description: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "description": self.description,
        }


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
            with work_flow_file_path.open(encoding="utf-8-sig") as f:
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
    deliverables: tuple[str, ...] = ()
    inputs: tuple[InputDeclaration, ...] = ()

    def get_node(self, node_id: str) -> WorkflowNodeModel | None:
        """Return the node with the given id, or None if not found."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    @staticmethod
    def _validate_deliverables(raw: object) -> tuple[str, ...]:
        """Validate the optional ``deliverables`` block for shape only.

        An absent block and an empty list are equivalent. The named artifacts are not checked
        against the registry: they exist only at runtime. Shape errors are aggregated. See ADR 011.
        """
        if raw is None:
            return ()
        if not isinstance(raw, list):
            raise WorkflowConfigurationError("deliverables must be a list of artifact names")
        errors: list[str] = []
        seen: set[str] = set()
        names: list[str] = []
        for index, item in enumerate(raw):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"entry {index} must be a non-empty string")
                continue
            if item in seen:
                errors.append(f"duplicate deliverable '{item}'")
                continue
            seen.add(item)
            names.append(item)
        if errors:
            raise WorkflowConfigurationError("Invalid deliverables: " + "; ".join(errors))
        return tuple(names)

    @staticmethod
    def _validate_inputs(raw: object) -> tuple[InputDeclaration, ...]:
        """Validate the optional ``inputs`` block for shape only. See ADR 012.

        An absent block and an empty list are equivalent. Each entry declares a unique ``name`` matching
        ``[A-Za-z_][A-Za-z0-9_]*``; an optional ``type`` must name a registered codec (full or bare) and is
        stored as the resolved full codec name; ``required`` defaults to true. Shape errors are aggregated.
        """
        if raw is None:
            return ()
        if not isinstance(raw, list):
            raise WorkflowConfigurationError("inputs must be a list of input declarations")
        errors: list[str] = []
        seen: set[str] = set()
        declarations: list[InputDeclaration] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                errors.append(f"entry {index} must be an object")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not _INPUT_NAME_RE.fullmatch(name):
                errors.append(f"entry {index}: name must match [A-Za-z_][A-Za-z0-9_]*")
                continue
            if name in seen:
                errors.append(f"duplicate input '{name}'")
                continue
            seen.add(name)
            raw_type = item.get("type")
            resolved_type: str | None = None
            if raw_type is not None:
                if not isinstance(raw_type, str):
                    errors.append(f"input '{name}': type must be a string")
                    continue
                try:
                    resolved_type = resolve_codec_by_type_name(raw_type).type_name()
                except WorkflowConfigurationError as exc:
                    errors.append(f"input '{name}': {exc}")
                    continue
            required = item.get("required", True)
            if not isinstance(required, bool):
                errors.append(f"input '{name}': required must be a boolean")
                continue
            description = item.get("description")
            if description is not None and not isinstance(description, str):
                errors.append(f"input '{name}': description must be a string")
                continue
            declarations.append(
                InputDeclaration(name=name, type=resolved_type, required=required, description=description)
            )
        if errors:
            raise WorkflowConfigurationError("Invalid inputs: " + "; ".join(errors))
        return tuple(declarations)

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
            deliverables=cls._validate_deliverables(data.get("deliverables")),
            inputs=cls._validate_inputs(data.get("inputs")),
        )
