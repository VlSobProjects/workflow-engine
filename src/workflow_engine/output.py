from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ParamWrite:
    mode: Literal["set", "replace", "append", "dict_update"]
    value: object
    allow_overwrite: bool = False


@dataclass
class ActionNodeOutput:
    output_text: str
    error_code: str | None = field(default=None)
    error_msg: str | None = field(default=None)
    param_writes: dict[str, ParamWrite] = field(default_factory=dict)

    def on_error(self) -> str:
        output_part = f", output: {self.output_text if self.output_text else ''}"
        return f"Error code {self.error_code}, message: {self.error_msg}{output_part}."

    def update_parameters(self, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        if prev_output is not None:
            self.param_writes.update(prev_output.param_writes)
        return self
