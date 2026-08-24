from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from workflow_engine.exceptions import StateLoadParameterError
from workflow_engine.models.state import GuardRecord
from workflow_engine.tools import (
    check_param_type,
    parameter_from_dict,
    parameter_from_dict_default,
    parameter_from_dict_optional,
)

RECORD_STATUS_COMPLETED = "completed"
RECORD_STATUS_FAILED = "failed"

WRITE_MODE_SAVE_AS = "SAVE_AS"

TRANSITION_KIND_NODE = "node"
TRANSITION_KIND_END = "end"
TRANSITION_KIND_FAIL = "fail"


@dataclass(frozen=True, slots=True)
class TransitionRecord:
    """The transition a visit took: to a node, to the end of the workflow, or into a failure.

    ``target`` is the node id for ``node``, the failure code for ``fail``, and absent for ``end``.
    See ADR 021 §1.
    """

    kind: Literal["node", "end", "fail"]
    target: str | None = field(default=None)

    @classmethod
    def to_node(cls, node_id: str) -> TransitionRecord:
        return cls(kind=TRANSITION_KIND_NODE, target=node_id)

    @classmethod
    def to_end(cls) -> TransitionRecord:
        return cls(kind=TRANSITION_KIND_END)

    @classmethod
    def to_failure(cls, code: str | None) -> TransitionRecord:
        return cls(kind=TRANSITION_KIND_FAIL, target=code)

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "target": self.target}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TransitionRecord:
        kind = parameter_from_dict(data, "kind", str)
        if kind not in (TRANSITION_KIND_NODE, TRANSITION_KIND_END, TRANSITION_KIND_FAIL):
            raise StateLoadParameterError(
                current_node="ANY",
                parameter_name="TransitionRecord.kind",
                message=f"Invalid transition kind: {kind}, allowed values: "
                f"('{TRANSITION_KIND_NODE}', '{TRANSITION_KIND_END}', '{TRANSITION_KIND_FAIL}')",
            )
        return cls(kind=kind, target=parameter_from_dict_optional(data, "target", str))


@dataclass(frozen=True, slots=True)
class ParamWriteRecord:
    """One applied parameter write, by name, codec name and write mode.

    The value is not here and never will be: the record stream carries names and codec names, the
    values live in the state. See ADR 021 §1 and ADR 013 §9.
    """

    name: str
    codec: str
    mode: str
    """The ``WriteParamMode`` the value was written in, or ``SAVE_AS`` for a node output saved by name."""

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "codec": self.codec, "mode": self.mode}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ParamWriteRecord:
        return cls(
            name=parameter_from_dict(data, "name", str),
            codec=parameter_from_dict(data, "codec", str),
            mode=parameter_from_dict(data, "mode", str),
        )

    @classmethod
    def from_list(cls, data: list) -> list[ParamWriteRecord]:
        return [cls.from_dict(check_param_type("item", dict, item)) for item in data if item is not None]


@dataclass(frozen=True, slots=True)
class NodeRecord:
    """One concluded node visit, as the engine appended it to the trail. See ADR 021 §1.

    A record describes effects that took hold: it is written after the output was applied and the
    transition was chosen. It names what the visit did — the action, the guards, the writes, the
    artifacts — and never carries a value.
    """

    node_id: str
    action: str
    status: Literal["completed", "failed"]
    transition: TransitionRecord
    visit: int = field(default=0)
    attempt: int = field(default=0)
    function: str | None = field(default=None)
    error_code: str | None = field(default=None)
    guards: list[GuardRecord] = field(default_factory=list)
    writes: list[ParamWriteRecord] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "node_id": self.node_id,
            "visit": self.visit,
            "attempt": self.attempt,
            "action": self.action,
            "function": self.function,
            "status": self.status,
            "error_code": self.error_code,
            "guards": [guard.to_dict() for guard in self.guards],
            "transition": self.transition.to_dict(),
            "writes": [write.to_dict() for write in self.writes],
            "artifacts": list(self.artifacts),
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> NodeRecord:
        status = parameter_from_dict(data, "status", str)
        if status not in (RECORD_STATUS_COMPLETED, RECORD_STATUS_FAILED):
            raise StateLoadParameterError(
                current_node=parameter_from_dict_default(data, "node_id", str, "ANY"),
                parameter_name="NodeRecord.status",
                message=f"Invalid record status: {status}, allowed values: "
                f"('{RECORD_STATUS_COMPLETED}', '{RECORD_STATUS_FAILED}')",
            )
        return cls(
            record_id=parameter_from_dict(data, "record_id", str),
            timestamp=datetime.fromisoformat(parameter_from_dict(data, "timestamp", str)),
            node_id=parameter_from_dict(data, "node_id", str),
            visit=parameter_from_dict_default(data, "visit", int, 0),
            attempt=parameter_from_dict_default(data, "attempt", int, 0),
            action=parameter_from_dict(data, "action", str),
            function=parameter_from_dict_optional(data, "function", str),
            status=status,
            error_code=parameter_from_dict_optional(data, "error_code", str),
            guards=GuardRecord.from_list(parameter_from_dict_default(data, "guards", list, [])),
            transition=TransitionRecord.from_dict(parameter_from_dict(data, "transition", dict)),
            writes=ParamWriteRecord.from_list(parameter_from_dict_default(data, "writes", list, [])),
            artifacts=[
                check_param_type("artifact", str, name)
                for name in parameter_from_dict_default(data, "artifacts", list, [])
                if name is not None
            ],
            details=parameter_from_dict_default(data, "details", dict, {}),
        )


@dataclass(frozen=True, slots=True)
class RecordPage:
    """A bounded read of the trail: what it carries, next to what the stream holds.

    ``total`` counts the whole stream, not the selection, because a bounded read that does not say
    it is bounded reads as the full record. See ADR 021 §4.
    """

    records: list[NodeRecord]
    total: int


class RecordSource(ABC):
    """The two operations the persistence contract gains for the trail. See ADR 021 §2."""

    @abstractmethod
    def append_record(self, session_id: str, record: NodeRecord) -> None:
        """Append one record to the session's stream. A record is never rewritten."""

    @abstractmethod
    def load_records(self, session_id: str, node_id: str | None = None, tail: int | None = None) -> RecordPage:
        """Read the session's stream, filtered by node first and bounded by tail last."""
