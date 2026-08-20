"""The core interactive action: a node that asks a question and waits for a typed answer. See ADR 013."""

from __future__ import annotations

from typing import ClassVar

from workflow_engine.actions.action_present import AnswerContract, PresentResponse
from workflow_engine.actions.base_actions import BaseInteractiveAction
from workflow_engine.exceptions import ActionConfigurationError
from workflow_engine.function_injection import run_action_function
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.models.workflow import validate_input_declarations
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.action_registry import (
    ActionExample,
    ActionOperatorMetadata,
    ActionParameterDoc,
    register_action,
)
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    FUNCTION_PARAMETERS_KEY,
    RegisteredFunctionExecutor,
)
from workflow_engine.tools import (
    parameter_from_dict,
    parameter_from_dict_default,
    parameter_from_dict_optional,
    render_value_as_text,
)

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
_FUNCTION_NAME_DOC = ActionParameterDoc(
    "str",
    "Registered function run on an accepted answer, before that answer becomes the output of the "
    "node. Its result is the node output: the text value guards compare, the parameter writes that "
    "land on the state, the artifacts it registered and the error code that routes a failure. A "
    "failure answer routes on its own code and never reaches the function.",
)
_FUNCTION_PARAMETERS_DOC = ActionParameterDoc(
    "dict",
    "Parameters passed to that function. Values support 'param.<name>', 'output.<node_id>' and "
    "'artifact.<logical_name>' references resolved from the workflow state, as in any node. The "
    "answered values are not among them: they have not reached the state yet and arrive through the "
    "injected 'output'.",
)

_POST_FUNCTION_NOTES = (
    "A function configured here is given the accepted answer as the injected 'output' parameter: an "
    "ActionNodeOutput whose 'output_text' is the answer text and whose parameter writes hold the "
    "answered values. Declare 'output' in the function signature to receive it, and 'state' for the "
    "read-only state view; both are injected and neither is configured.",
    "What the function returns is the whole output of the node, parameter writes included: a function "
    "that builds a fresh result instead of editing the one it was given drops the answered values "
    "before they reach the state.",
    "'save_as' stores the output text of the node, which with a function configured here is the text "
    "the function returned and no longer the text that was answered.",
    "The answer is journaled as it was supplied. What the function made of it is the output of the "
    "node, journaled the way any node output is.",
)


def _resolve_text(state: StateReadOnlyView, value: str) -> str:
    """Resolve one presentation string, which may be a 'param.'/'output.'/'artifact.' reference.

    A reference is resolved as a whole value, as everywhere else in a node configuration; a resolved
    value that is not a string is rendered, because a presentation is text. A path is rendered in
    POSIX form: the presentation is published in the command result, and ADR 008 holds there too.
    """
    return render_value_as_text(state.set_parameters({"value": value})["value"])


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
    notes=list(_POST_FUNCTION_NOTES),
    metadata=ActionOperatorMetadata(
        description=(
            "Presents a question to whoever runs the workflow — an operator, an agent, or a program — "
            "and stops the run. The command reports a paused workflow (exit code 2) and carries the "
            "question and the declared answer in 'data.question'. The run continues with "
            "'resume --answer' or 'resume --answer-file': a success answer binds its declared values "
            "into the state and routes through the node's transitions, a failure answer routes on its "
            "error code, and a plain 'resume' presents the same question again. With 'function_name' a "
            "registered function runs on an accepted answer and its result becomes the output of the "
            "node, so the answer can be routed on, accumulated or normalized without a second node."
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
            "function_name": _FUNCTION_NAME_DOC,
            "function_parameters": _FUNCTION_PARAMETERS_DOC,
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
            "With 'function_name' the guards route on what the function returned, not on what was "
            "answered, and a function that reports an error code fails the node under it.",
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

    An optional registered function computes on the answer once it is accepted, the way 'stop' runs
    one only when it is configured. Composition, not a second action and not a second hierarchy: the
    question stays declarative when no function is configured. See ADR 015 §8.
    """

    ACTION_TYPE: ClassVar[str] = "ask"
    registered_function: RegisteredFunctionExecutor[ActionNodeOutput] | None

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
        self.registered_function = self.get_registered_action_function(data) if FUNCTION_NAME_KEY in data else None
        if self.registered_function is None and FUNCTION_PARAMETERS_KEY in data:
            raise ActionConfigurationError(
                self.ACTION_TYPE,
                f"'{FUNCTION_PARAMETERS_KEY}' configures a function this node does not run; "
                f"declare '{FUNCTION_NAME_KEY}' or remove it",
            )

    def _process_answer(self, state: StateReadOnlyView, output: ActionNodeOutput) -> ActionNodeOutput:
        """Run the configured function on the accepted answer and return its result. See ADR 015 §4."""
        if self.registered_function is None:
            return output
        return run_action_function(self.registered_function, state, output)

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
