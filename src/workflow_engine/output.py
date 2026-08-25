from __future__ import annotations

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
    details: dict[str, object] = field(default_factory=dict)
    """What the action did, for the record of the visit: the open member of ADR 021 §1.

    The engine copies it into the node record and reads nothing in it, the way a provider reads its
    call options. It carries facts about the work — which provider answered, which model, what it
    cost — never values: those are in the writes and the artifacts. An action that has nothing to
    account for leaves it empty, which is every action but ``llm`` today. See ADR 014 §4.
    """

    def get_param(self, name: str, default: object = None) -> object:
        """Read one value this output writes to the bus, without reading the write modes.

        The counterpart of ``StateReadOnlyView.get_param`` for a value that has not landed yet: a
        function post-processing an answer reads what was answered here, because an answer reaches
        the bus only after the transition is selected. See ADR 015 §3.
        """
        param_write = self.param_writes.get(name)
        return default if param_write is None else param_write.value

    def set_param(self, name: str, value: object, allow_overwrite: bool = True) -> None:
        """Write one value as a ``SET``, replacing whatever this output wrote under that name.

        ``SET`` only, on purpose: every other write mode stays spelled out in ``param_writes``, so no
        helper ever hides what a node does to a collection. Overwriting is allowed by default because
        a question asked again in a loop answers the same names.
        """
        self.param_writes[name] = ParamWrite(mode=WriteParamMode.SET, value=value, allow_overwrite=allow_overwrite)

    def on_error(self) -> str:
        output_part = f", output: {self.output_text if self.output_text else ''}"
        return f"Error code {self.error_code}, message: {self.error_msg}{output_part}."
