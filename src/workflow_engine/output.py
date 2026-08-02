from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ActionNodeOutput:
    output_text: str
    error_code: str | None = field(default=None)
    error_message: str | None = field(default=None)
    parameters: dict[str, object] = field(default_factory=dict)

    def on_error(self) -> str:
        output_part = f", output: {self.output_text if self.output_text else ''}"
        return f"Error code {self.error_code}, message: {self.error_message}{output_part}."

    def update_parameters(self, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        if prev_output is not None:
            self.parameters.update(prev_output.parameters)
        return self
