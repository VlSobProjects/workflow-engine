from dataclasses import dataclass, field

from workflow_engine.models.workflow import InputDeclaration


@dataclass(frozen=True)
class AnswerContract:
    """What a valid answer to an interactive node must carry. See ADR 013 §2.

    The declarations are the machine-readable replacement of the free-text ``expected_input``: they name
    the parameters an answer binds and how each is typed. The catalogue names the failure codes the node
    accepts, which is why it is not ``PresentResponse.errors``: that field reports what actually failed.
    """

    declarations: tuple[InputDeclaration, ...] = ()
    error_catalogue: dict[str, str] = field(default_factory=dict)

    def declared_codes(self) -> frozenset[str]:
        return frozenset(self.error_catalogue)

    def to_dict(self) -> dict[str, object]:
        return {
            "declarations": [declaration.to_dict() for declaration in self.declarations],
            "error_catalogue": dict(self.error_catalogue),
        }


@dataclass
class PresentResponse:
    title: str = field(metadata={"label": "Title", "description": "Short title of the question"})
    description: str = field(metadata={"label": "Description", "description": "Description of action"})
    instruction: str = field(metadata={"label": "Instruction", "description": "Main instruction for the LLM"})
    goal: str | None = field(
        default=None, metadata={"label": "Goal", "description": "The goal or objective for the agent"}
    )
    options: list[str] | None = field(
        default=None,
        metadata={"label": "Options", "description": "List of available options for the user to choose from"},
    )
    errors: dict[str, str] | None = field(
        default=None, metadata={"label": "Errors", "description": "List error with descriptions"}
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
    hints: list[str] | None = field(default=None, metadata={"label": "Hints", "description": "Hints for agent"})
    constraints: list[str] | None = field(
        default=None, metadata={"label": "Constraints", "description": "Constraints for agent"}
    )
    examples: list[str] | None = field(
        default=None, metadata={"label": "Examples", "description": "Examples for agent"}
    )
    answer: AnswerContract | None = field(
        default=None,
        metadata={"label": "Answer", "description": "Declared shape of a valid answer to an interactive node"},
    )
