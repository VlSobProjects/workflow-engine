from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_optional


@dataclass(frozen=True)
class WorkflowArtifact:
    relative_path: Path
    created_at: datetime
    description: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path.as_posix(),
            "created_at": self.created_at.isoformat(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowArtifact:
        relative_path = Path(parameter_from_dict(data, "relative_path", str))
        created_at = datetime.fromisoformat(parameter_from_dict(data, "created_at", str))
        description = parameter_from_dict_optional(data, "description", str)
        return WorkflowArtifact(relative_path=relative_path, created_at=created_at, description=description)


@dataclass(frozen=True)
class ParamWrite:
    mode: WriteParamMode
    value: object
    allow_overwrite: bool = False


@dataclass
class ActionNodeOutput:
    output_text: str
    error_code: str | None = field(default=None)
    error_msg: str | None = field(default=None)
    param_writes: dict[str, ParamWrite] = field(default_factory=dict)
    artifacts: dict[str, WorkflowArtifact] = field(default_factory=dict)

    def on_error(self) -> str:
        output_part = f", output: {self.output_text if self.output_text else ''}"
        return f"Error code {self.error_code}, message: {self.error_msg}{output_part}."

    @classmethod
    def from_args(cls, args: Namespace) -> ActionNodeOutput | None:
        if not hasattr(args, "input") and not hasattr(args, "error_code"):
            return None
        output_text = getattr(args, "input", "")
        error_code = getattr(args, "error_code", None)
        error_msg = getattr(args, "error_msg", None)
        param_writes = getattr(args, "param_writes", {})
        artifacts = getattr(args, "artifacts", {})
        return cls(
            output_text=output_text,
            error_code=error_code,
            error_msg=error_msg,
            param_writes=param_writes,
            artifacts=artifacts
        )
