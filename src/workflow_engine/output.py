from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from workflow_engine.collection_param_handlers import WriteParamMode


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
    artifacts: dict[str, Path] = field(default_factory=dict)

    def on_error(self) -> str:
        output_part = f", output: {self.output_text if self.output_text else ''}"
        return f"Error code {self.error_code}, message: {self.error_msg}{output_part}."
