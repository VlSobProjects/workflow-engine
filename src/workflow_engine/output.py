from dataclasses import dataclass, field


@dataclass
class ActionNodeOutput:
    output: str
    error_code: str | None = field(default=None)
    error_message: str | None = field(default=None)