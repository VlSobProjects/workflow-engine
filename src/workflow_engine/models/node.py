from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkflowNodeModel:
    id: str
    action_type: str
    action_parameters: dict[str, object]
    save_as: str | None = field(default=None)
    transition: dict[str, object] | None = field(default=None)
    validator: dict[str, object] | None = field(default=None)
    max_attempts: int = field(default=3)



