from __future__ import annotations

from dataclasses import dataclass, field

from workflow_engine.tools import parameter_from_dict, parameter_from_dict_default, parameter_from_dict_optional


@dataclass(frozen=True)
class WorkflowNodeModel:
    id: str
    action_type: str
    action_parameters: dict[str, object]
    save_as: str | None = field(default=None)
    transitions: list[dict[str, object]] | None = field(default=None)
    validators: list[dict[str, object]] | None = field(default=None)
    max_attempts: int = field(default=3)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowNodeModel:
        return cls(
            id=parameter_from_dict(data, "id", str),
            action_type=parameter_from_dict(data, "action_type", str),
            action_parameters=parameter_from_dict(data, "action_parameters", dict),
            save_as=parameter_from_dict_optional(data, "save_as", str),
            transitions=parameter_from_dict_optional(data, "transitions", list),
            validators=parameter_from_dict_optional(data, "validators", list),
            max_attempts=parameter_from_dict_default(data, "max_attempts", int, 3),
        )
