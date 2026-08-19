"""The core interactive action: a node that asks a question and waits for a typed answer. See ADR 013."""

from __future__ import annotations

from typing import ClassVar

from workflow_engine.actions.action_present import AnswerContract, PresentResponse
from workflow_engine.actions.base_actions import BaseInteractiveAction
from workflow_engine.exceptions import ActionConfigurationError
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.models.workflow import validate_input_declarations
from workflow_engine.registry.action_registry import (
    ActionExample,
    ActionOperatorMetadata,
    ActionParameterDoc,
    register_action,
)
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_default, parameter_from_dict_optional

DEFAULT_TITLE = "Question"

_ANSWER_KEY = "answer"
_LIST_KEYS = ("options", "requirements", "constraints", "examples", "hints")

_ANSWER_DOC = ActionParameterDoc(
    "list",
    "Declaration of the answer, in the shape of the workflow 'inputs' block: each entry has a 'name', "
    "an optional codec 'type', a 'required' flag (default true) and an optional 'description'. "
    "An empty list declares a question that binds no parameter and is routed by its answer text.",
)
_ERRORS_DOC = ActionParameterDoc(
    "dict",
    "Error catalogue of the node: failure code to description. A failure answer must use one of these "
    "codes or the generic 'answer_failed'.",
)


def _resolve_text(state: StateReadOnlyView, value: str) -> str:
    """Resolve one presentation string, which may be a 'param.'/'output.'/'artifact.' reference.

    A reference is resolved as a whole value, as everywhere else in a node configuration; a resolved
    value that is not a string is rendered, because a presentation is text.
    """
    resolved = state.set_parameters({"value": value})["value"]
    return resolved if isinstance(resolved, str) else str(resolved)


def _string_list(data: dict[str, object], key: str) -> list[str] | None:
    raw = parameter_from_dict_optional(data, key, list)
    if raw is None:
        return None
    if not all(isinstance(item, str) for item in raw):
        raise ActionConfigurationError(AskAction.ACTION_TYPE, f"'{key}' must be a list of strings")
    return [str(item) for item in raw]


def _string_map(data: dict[str, object], key: str) -> dict[str, str]:
    raw = parameter_from_dict_optional(data, key, dict)
    if raw is None:
        return {}
    if not all(isinstance(name, str) and isinstance(text, str) for name, text in raw.items()):
        raise ActionConfigurationError(AskAction.ACTION_TYPE, f"'{key}' must map string codes to string descriptions")
    return dict(raw)


@register_action(
    "Asks a question and pauses the run until a typed answer arrives.",
    metadata=ActionOperatorMetadata(
        description=(
            "Presents a question to whoever runs the workflow — an operator, an agent, or a program — "
            "and stops the run. The command reports a paused workflow (exit code 2) and carries the "
            "question and the declared answer in 'data.question'. The run continues with "
            "'resume --answer' or 'resume --answer-file': a success answer binds its declared values "
            "into the state and routes through the node's transitions, a failure answer routes on its "
            "error code, and a plain 'resume' presents the same question again."
        ),
        required_parameters={
            "instruction": ActionParameterDoc("str", "The question itself: what the answerer has to do."),
            _ANSWER_KEY: _ANSWER_DOC,
        },
        optional_parameters={
            "title": ActionParameterDoc("str", f"Short title of the question (default '{DEFAULT_TITLE}')."),
            "description": ActionParameterDoc(
                "str", "One line describing the node; defaults to the instruction, and becomes the result message."
            ),
            "goal": ActionParameterDoc("str", "The objective the answer serves."),
            "context": ActionParameterDoc("str", "Context the answerer needs."),
            "options": ActionParameterDoc("list", "The answers to choose from."),
            "requirements": ActionParameterDoc("list", "What the answer must satisfy."),
            "constraints": ActionParameterDoc("list", "What the answerer must not do."),
            "examples": ActionParameterDoc("list", "Example answers."),
            "hints": ActionParameterDoc("list", "Hints for the answerer."),
            "errors": _ERRORS_DOC,
        },
        node_template={
            "id": "<node-id>",
            "action_type": "ask",
            "action_parameters": {
                "instruction": "<the question>",
                "answer": [{"name": "<parameter>", "type": "<codec>", "required": True}],
            },
            "transitions": [{"next": "<next-node-id>"}],
        },
        transition_hints=(
            "A success answer produces no error code, so a 'no_error' guard routes the normal path.",
            "Route a failure answer with an 'errors' transition on the codes declared in 'errors', "
            "plus the generic 'answer_failed'.",
            "Value guards compare the optional answer 'text', which is the output text of the node.",
            "A transition back to the node itself asks again and is bounded by 'max_attempts'.",
        ),
        examples=(
            ActionExample(
                title="Ask an operator to approve a generated report",
                node={
                    "id": "APPROVE_REPORT",
                    "action_type": "ask",
                    "action_parameters": {
                        "title": "Approve the report",
                        "instruction": (
                            "Read the report and answer with 'approved' or 'rejected' as the answer text, "
                            "naming yourself in 'reviewer'."
                        ),
                        "context": "artifact.report_csv",
                        "options": ["approved", "rejected"],
                        "answer": [{"name": "reviewer", "description": "Who reviewed the report"}],
                        "errors": {"report_unreadable": "The report could not be opened."},
                    },
                    "transitions": [
                        {"next": "PUBLISH", "validator": {"equals": "approved"}},
                        {"next": "REWORK", "validator": {"equals": "rejected"}},
                        {"errors": ["report_unreadable", "answer_failed"], "fail": "review_failed"},
                    ],
                },
            ),
        ),
    ),
)
class AskAction(BaseInteractiveAction):
    """Asks a question and pauses the run until a typed answer arrives.

    The action is indifferent to who answers: an operator, an agent, or a calling program all use one
    contract, and who answered is recorded as data about the answer. See ADR 013 §1.
    """

    ACTION_TYPE: ClassVar[str] = "ask"

    def __init__(self, data: dict[str, object]) -> None:
        if _ANSWER_KEY not in data:
            raise ActionConfigurationError(
                self.ACTION_TYPE,
                "the 'answer' declaration is required; declare [] for a question that binds no parameter",
            )
        self.instruction = parameter_from_dict(data, "instruction", str)
        self.title = parameter_from_dict_default(data, "title", str, DEFAULT_TITLE)
        self.description = parameter_from_dict_default(data, "description", str, self.instruction)
        self.goal = parameter_from_dict_optional(data, "goal", str)
        self.context = parameter_from_dict_optional(data, "context", str)
        self.lists = {key: _string_list(data, key) for key in _LIST_KEYS}
        self.error_catalogue = _string_map(data, "errors")
        self.declarations = validate_input_declarations(data.get(_ANSWER_KEY), _ANSWER_KEY)

    def answer_contract(self) -> AnswerContract:
        return AnswerContract(declarations=self.declarations, error_catalogue=dict(self.error_catalogue))

    def present(self, state: StateReadOnlyView) -> PresentResponse:
        resolved_lists = {
            key: None if value is None else [_resolve_text(state, item) for item in value]
            for key, value in self.lists.items()
        }
        return PresentResponse(
            title=_resolve_text(state, self.title),
            description=_resolve_text(state, self.description),
            instruction=_resolve_text(state, self.instruction),
            goal=None if self.goal is None else _resolve_text(state, self.goal),
            context=None if self.context is None else _resolve_text(state, self.context),
            answer=self.answer_contract(),
            **resolved_lists,
        )
