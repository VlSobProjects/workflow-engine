from dataclasses import dataclass, field
from enum import Enum


def default_hints() -> list[str]:
    return ["Use ';' delimit to submit multiple values"]


def default_submit() -> str:
    return """
    On Success: [task_success] and any requested in instruction values if any.
    
    On Error: [error_code] from errors with brif reasoning.
    """


def def_errors() -> dict[str, str]:
    return {
        "other_error": "Submit this error if none of the other errors apply but you are unable to complete the task."
    }


@dataclass
class PresentResponse:
    title: str = field(metadata={"label": "Title", "description": "Short title of the question"})
    description: str = field(metadata={"label": "Description", "description": "Description of action"})
    instruction: str = field(metadata={"label": "Instruction", "description": "Main instruction for the LLM"})
    submit: str | None = field(
        default_factory=default_submit,
        metadata={"label": "Submit", "description": "Submit one or multiple parameters after performing an action"},
    )
    goal: str | None = field(
        default=None, metadata={"label": "Goal", "description": "The goal or objective for the agent"}
    )
    options: list[str] | None = field(
        default=None,
        metadata={"label": "Options", "description": "List of available options for the user to choose from"},
    )
    errors: dict[str, str] | None = field(
        default_factory=def_errors, metadata={"label": "Errors", "description": "List error with descriptions"}
    )
    requirements: list[str] | None = field(
        default=None,
        metadata={
            "label": "Requirements",
            "description": "List of requirements for the agent to fulfill form conversation context",
        },
    )
    context: str | None = field(
        default=None, metadata={"label": "Context", "description": "Context information for the agent"}
    )
    expected_input: str | None = field(
        default=None, metadata={"label": "Expected User Input", "description": "Expected input from the user"}
    )
    hints: list[str] | None = field(
        default_factory=default_hints, metadata={"label": "Hints", "description": "Hints for agent"}
    )
    constraints: list[str] | None = field(
        default=None, metadata={"label": "Constraints", "description": "Constraints for agent"}
    )
    examples: list[str] | None = field(
        default=None, metadata={"label": "Examples", "description": "Examples for agent"}
    )


class SubmitStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"


@dataclass(slots=True)
class SubmitResult:
    status: SubmitStatus
    message: str | None
    payload: dict[str, object] | None = field(default=None)
