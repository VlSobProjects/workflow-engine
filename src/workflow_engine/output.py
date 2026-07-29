from dataclasses import dataclass, field


@dataclass
class ActionNodeOutput:
    output_text: str
    error_code: str | None = field(default=None)
    error_message: str | None = field(default=None)

    def on_error(self)->str:
        return f"Error code {self.error_code}, message: {self.error_message}{f", output: {self.output_text if self.output_text else ''}"}."