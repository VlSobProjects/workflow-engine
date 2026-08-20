from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from workflow_engine.exceptions import WorkflowParameterError
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_default, parameter_from_dict_optional

ACTION_TYPE_KEY: Final[str] = "action_type"
ACTION_PARAMS_KEY: Final[str] = "action_parameters"


def _max_visits_from_dict(data: dict[str, object]) -> int | None:
    """The declared per-node visit cap, or None for a node nothing bounds but the ADR 010 caps.

    Absence is the only way to say unbounded, so that only a declared node is capped (ADR 017 §2). A
    declared value below one would refuse the node on its very first entry, which no author means by
    writing the key; it is a configuration error rather than a silent second spelling of "unbounded".
    """
    max_visits = parameter_from_dict_optional(data, "max_visits", int)
    if max_visits is not None and max_visits < 1:
        raise WorkflowParameterError("max_visits", int, int, "Declared visit cap must be at least 1")
    return max_visits


@dataclass(frozen=True)
class WorkflowNodeModel:
    id: str
    action_type: str
    action_parameters: dict[str, object]
    save_as: str | None = field(default=None)
    transitions: list[dict[str, object]] | None = field(default=None)
    validators: list[dict[str, object]] | None = field(default=None)
    max_attempts: int = field(default=3)
    max_visits: int | None = field(default=None)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowNodeModel:
        return cls(
            id=parameter_from_dict(data, "id", str),
            action_type=parameter_from_dict(data, ACTION_TYPE_KEY, str),
            action_parameters=parameter_from_dict(data, ACTION_PARAMS_KEY, dict),
            save_as=parameter_from_dict_optional(data, "save_as", str),
            transitions=parameter_from_dict_optional(data, "transitions", list),
            validators=parameter_from_dict_optional(data, "validators", list),
            max_attempts=parameter_from_dict_default(data, "max_attempts", int, 3),
            max_visits=_max_visits_from_dict(data),
        )
