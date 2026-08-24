"""The core automatic action: a node that calls a model and binds its reply. See ADR 014 §1.

The counterpart of the interactive ``ask``: the two share the answer declaration of ADR 013 and sit
on opposite sides of one boundary. ``ask`` binds an answer produced outside the engine and pauses
until it arrives; ``llm`` performs the call itself inside the run, parses the reply, decodes the
declared values through their codecs and audits what it did. No provider semantics live here: the
action knows a prompt, a model name, opaque call options and the fixed error classes, and nothing
about the protocol behind them.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from workflow_engine.actions.base_actions import BaseAutomaticAction
from workflow_engine.declared_values import bind_declared_values
from workflow_engine.exceptions import ActionConfigurationError, WorkflowConfigurationError, WorkflowInputError
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.models.workflow import validate_input_declarations
from workflow_engine.output import ActionNodeOutput, WorkflowArtifact
from workflow_engine.providers.base_provider import ProviderCall, ProviderErrorClass, ProviderReply
from workflow_engine.providers.provider_seat import resolve_provider
from workflow_engine.registry.action_registry import (
    ActionExample,
    ActionOperatorMetadata,
    ActionParameterDoc,
    register_action,
)
from workflow_engine.text_interpolation import resolve_template_text, validate_template_text
from workflow_engine.tools import (
    parameter_from_dict,
    parameter_from_dict_default,
    parameter_from_dict_optional,
)

LLM_ANSWER_INVALID = "llm_answer_invalid"
"""The reply did not fit the answer declaration: unreadable, or missing or unknown names."""

PROVIDER_FAILED = "provider_failed"
"""The adapter raised instead of returning a classified failure, so it broke the contract itself."""

LLM_RECORD_FAILED = "llm_record_failed"
"""The call succeeded but its audit artifacts could not be written, and 'record' asked for them."""

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
FORMATS = (FORMAT_TEXT, FORMAT_JSON)

ANSWER_KEY = "answer"
FORMAT_KEY = "format"
OPTIONS_KEY = "options"
RECORD_KEY = "record"

CALL_STATUS_ANSWERED = "answered"
CALL_STATUS_FAILED = "failed"

AUDIT_DIR = "llm"

_ERROR_CLASS_CODES = tuple(item.value for item in ProviderErrorClass)

_NOTES = (
    "The prompt is template text: '${param.<name>}', '${output.<node_id>}' and "
    "'${artifact.<logical_name>}' are replaced by the referenced value when the node runs, '$$' "
    "writes a literal '$', and an inserted value is never re-scanned, so a value full of '$' needs "
    "no escaping and cannot smuggle a reference in.",
    "A malformed template is a configuration error of the node, reported when the workflow is "
    "loaded; a reference that does not resolve fails the run at the call. Neither is routable.",
    "The node error codes are the six provider error classes as they are - "
    + ", ".join(_ERROR_CLASS_CODES)
    + f" - plus '{LLM_ANSWER_INVALID}' for a reply that does not fit the answer declaration, "
    f"'{PROVIDER_FAILED}' for an adapter that raised instead of classifying its failure, and "
    f"'{LLM_RECORD_FAILED}' when 'record' is set and the audit artifacts cannot be written.",
    "A provider the configuration does not declare, an adapter no loaded module registered and a "
    "call with no model resolved are configuration errors, not routable node errors.",
    "Every call is accounted for in the record of the visit: the provider, the model, the status of "
    "the call, the error class and the token counts the adapter reported. Read them with "
    "'show-records'.",
    "'save_as' stores the output text of the node, which is the raw reply exactly as the model "
    "produced it, before any parsing.",
)


def _audit_name(node_id: str, kind: str, visit: int, attempt: int) -> str:
    return f"{node_id}.{kind}.{visit}.{attempt}"


@register_action(
    "Calls a model through a registered provider adapter and binds its reply.",
    notes=list(_NOTES),
    metadata=ActionOperatorMetadata(
        description=(
            "Resolves the prompt against the state, calls the model of a configured provider, and "
            "turns the reply into the output of the node: the raw reply is the output text, and the "
            "values the reply carries are decoded through their codecs into the declared parameters. "
            "The run does not pause - this is the automatic counterpart of 'ask', and it shares the "
            "'answer' declaration with it. Every failure of the call is a node error code a "
            "transition can route, so a retry, a smaller chunk or a different branch stays a "
            "decision of the graph rather than a hidden behaviour of the action."
        ),
        required_parameters={
            "provider": ActionParameterDoc(
                "str",
                "Name of a provider declared in the 'providers' section of the engine configuration "
                "file, not the name of the adapter it uses.",
            ),
            "prompt": ActionParameterDoc("str", "The prompt sent to the model.", template=True),
            ANSWER_KEY: ActionParameterDoc(
                "list",
                "Declaration of what the reply must yield, in the shape of the workflow 'inputs' "
                "block: each entry has a 'name', an optional codec 'type', a 'required' flag "
                "(default true) and an optional 'description'. Declare [] for a call whose reply is "
                "only the output text.",
            ),
        },
        optional_parameters={
            "model": ActionParameterDoc(
                "str", "Model identifier passed to the adapter; defaults to the model of the provider block."
            ),
            FORMAT_KEY: ActionParameterDoc(
                "str",
                f"How the reply is read: '{FORMAT_TEXT}' (default) binds the whole reply to the one "
                f"declared name, '{FORMAT_JSON}' reads a JSON object whose keys are the declared "
                f"names. Under '{FORMAT_TEXT}' the declaration holds at most one entry.",
            ),
            OPTIONS_KEY: ActionParameterDoc(
                "dict",
                "Call options passed to the adapter unread - temperature, token limits, and anything "
                "else the named adapter understands, including an instruction about its own "
                "resources such as releasing the model after this call. Ask 'show-component "
                "--component-type provider' which options an adapter acts on.",
            ),
            RECORD_KEY: ActionParameterDoc(
                "bool",
                "Write the prompt and the reply as artifacts of the run, named after the node and "
                "numbered by the visit and the attempt, so a call can be read back or declared a "
                "deliverable. Default false.",
            ),
        },
        node_template={
            "id": "<node-id>",
            "action_type": "llm",
            "action_parameters": {
                "provider": "<configured-provider>",
                "prompt": "<the prompt>",
                ANSWER_KEY: [{"name": "<parameter>", "type": "<codec>", "required": True}],
                FORMAT_KEY: FORMAT_JSON,
            },
            "transitions": [{"next": "<next-node-id>"}],
        },
        transition_hints=(
            "A successful call produces no error code, so a 'no_error' guard routes the normal path.",
            "Route the failures with an 'errors' transition on the classes the branch handles: "
            "'transient' and 'rate_limited' back to the node itself with 'attempts', bounded by the "
            "node's 'max_attempts'; 'context_overflow' into a branch that splits the data and calls "
            "the model per chunk.",
            f"'{LLM_ANSWER_INVALID}' is the reply the declaration refused; a transition back to the "
            "node asks the model again, bounded by 'max_attempts'.",
            "Value guards compare the raw reply, which is the output text of the node.",
        ),
        examples=(
            ActionExample(
                title="Classify a file and write the verdict into two typed parameters",
                node={
                    "id": "CLASSIFY_FILE",
                    "action_type": "llm",
                    "action_parameters": {
                        "provider": "local",
                        "prompt": (
                            "Classify the file ${param.current_file}. Answer with a JSON object "
                            'holding "category" and "confidence".'
                        ),
                        ANSWER_KEY: [
                            {"name": "category", "description": "The category of the file"},
                            {"name": "confidence", "type": "float", "required": False},
                        ],
                        FORMAT_KEY: FORMAT_JSON,
                        OPTIONS_KEY: {"temperature": 0},
                        RECORD_KEY: True,
                    },
                    "max_attempts": 3,
                    "transitions": [
                        {"next": "NEXT_FILE", "guard": {"no_error": True}},
                        {"errors": ["transient", "rate_limited"], "next": "CLASSIFY_FILE", "attempts": True},
                        {"errors": ["context_overflow"], "next": "SPLIT_FILE"},
                        {"errors": ["llm_answer_invalid"], "fail": "classification_unusable"},
                    ],
                },
            ),
        ),
    ),
)
class LlmAction(BaseAutomaticAction):
    """Calls a model through a registered provider adapter and binds its reply. See ADR 014 §1.

    The action owns three things and delegates everything else: how the reply is read into raw
    values ('format'), what a reply that does not fit the declaration becomes (a routable error
    value), and what the call leaves behind for the audit. Decoding those raw values into typed
    parameters is the one code path it shares with the answer binding of ADR 013, so the two
    declarations cannot drift apart; reaching the provider is the adapter's business alone.
    """

    ACTION_TYPE: ClassVar[str] = "llm"

    def __init__(self, data: dict[str, object]) -> None:
        if ANSWER_KEY not in data:
            raise ActionConfigurationError(
                self.ACTION_TYPE,
                f"the '{ANSWER_KEY}' declaration is required; declare [] for a call that binds no parameter",
            )
        self.provider = parameter_from_dict(data, "provider", str)
        self.model = parameter_from_dict_optional(data, "model", str)
        self.prompt = parameter_from_dict(data, "prompt", str)
        self.declarations = validate_input_declarations(data.get(ANSWER_KEY), ANSWER_KEY)
        self.format = parameter_from_dict_default(data, FORMAT_KEY, str, FORMAT_TEXT)
        self.options = dict(parameter_from_dict_optional(data, OPTIONS_KEY, dict) or {})
        self.record = parameter_from_dict_default(data, RECORD_KEY, bool, False)
        if self.format not in FORMATS:
            raise ActionConfigurationError(
                self.ACTION_TYPE, f"'{FORMAT_KEY}' must be one of {list(FORMATS)}, got '{self.format}'"
            )
        if self.format == FORMAT_TEXT and len(self.declarations) > 1:
            # A text reply is one value, so a second declared name could only be filled by guessing
            # where the reply divides. An author who needs two names asks for 'json'. See ADR 014 §1.
            raise ActionConfigurationError(
                self.ACTION_TYPE,
                f"'{FORMAT_KEY}: {FORMAT_TEXT}' reads the whole reply as one value, so it binds at most one "
                f"declared name; this node declares {[item.name for item in self.declarations]}. "
                f"Use '{FORMAT_KEY}: {FORMAT_JSON}' for a reply carrying several names.",
            )
        validate_template_text(self.ACTION_TYPE, "prompt", self.prompt)

    def _raw_values(self, reply_text: str) -> dict[str, object]:
        """Read the raw values out of the reply, by the declared format. See ADR 014 §1.

        Extraction is the action's own concern, unlike the decoding that follows it: what a reply
        looks like is a property of the call, while what a declared name means is a property of the
        declaration and is therefore shared with the answer binding of ADR 013.
        """
        if self.format == FORMAT_TEXT:
            if not self.declarations:
                return {}
            return {self.declarations[0].name: reply_text}
        try:
            parsed = json.loads(reply_text)
        except json.JSONDecodeError as exc:
            raise WorkflowInputError(f"the reply is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise WorkflowInputError("the reply must be a JSON object of declared name to value")
        return parsed

    def _details(self, model: str, reply: ProviderReply | None, error_class: str | None) -> dict[str, object]:
        """The account of one call, for the record of the visit. See ADR 014 §4 and ADR 021 §1.

        Names and numbers, never values: what the model was asked and what it answered are the
        prompt and the reply, which live in the output text and, when the node opts in, in artifacts.
        """
        details: dict[str, object] = {
            "provider": self.provider,
            "model": (reply.model if reply is not None and reply.model else model),
            "status": CALL_STATUS_FAILED if error_class is not None else CALL_STATUS_ANSWERED,
        }
        if error_class is not None:
            details["error_class"] = error_class
        if reply is not None and reply.usage is not None:
            details["usage"] = reply.usage.to_dict()
        return details

    def _audit_artifacts(
        self, state: StateReadOnlyView, prompt: str, reply_text: str | None
    ) -> dict[str, WorkflowArtifact]:
        """Write the prompt and the reply of this call as artifacts of the run. See ADR 014 §4.

        They are numbered by the visit and the attempt the node is in, the ordinals the record of the
        visit carries, so the artifacts of one call and its record are found by the same two numbers.
        A failed call has no reply to write; its classified failure is in the record.
        """
        node_id = state.current_node_id
        visit, attempt = state.visit_ordinals(node_id)
        written: dict[str, WorkflowArtifact] = {}
        contents = [("prompt", prompt)] if reply_text is None else [("prompt", prompt), ("reply", reply_text)]
        for kind, content in contents:
            name = _audit_name(node_id, kind, visit, attempt)
            relative_path = state.get_artifact_relative_path(Path(AUDIT_DIR) / f"{name}.txt")
            absolute_path = state.get_artifact_absolute_path(relative_path)
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            with absolute_path.open("w", encoding="utf-8", newline="\n") as file:
                file.write(content)
            written[name] = WorkflowArtifact(
                relative_path, datetime.now(tz=UTC), description=f"The {kind} of the model call in node {node_id}"
            )
        return written

    def _failed_call_artifacts(self, state: StateReadOnlyView, prompt: str) -> dict[str, WorkflowArtifact]:
        """The prompt of a failed call, where the node opted in, and nothing where it cannot be written.

        A failed call carries its classification already, so a file that could not be written must
        not turn one failure into a different one.
        """
        if not self.record:
            return {}
        try:
            return self._audit_artifacts(state, prompt, None)
        except OSError:
            return {}

    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        """Resolve the prompt, call the provider, and turn the reply into the output of the node.

        Three failures are configuration errors and none of them is routable: a provider the
        installation does not configure, an adapter no loaded module registered, and a call for which
        neither the node nor the provider block names a model. They are wrong before the run rather
        than during it, so a transition must not be able to paper over them. See ADR 014 §3.
        """
        prompt = resolve_template_text(state, self.prompt)
        provider = resolve_provider(self.provider)
        model = provider.resolve_model(self.model)
        if model is None:
            raise WorkflowConfigurationError(
                f"Node '{state.current_node_id}' calls provider '{self.provider}' without a model: "
                f"the node declares none and the provider block has no default 'model'."
            )

        call = ProviderCall(prompt=prompt, model=model, options=MappingProxyType(dict(self.options)))
        try:
            reply = provider.complete(call)
        except Exception as e:  # noqa: BLE001 - an adapter that raises broke the contract, and the node routes it
            return ActionNodeOutput(
                output_text="",
                error_code=PROVIDER_FAILED,
                error_msg=f"Provider '{self.provider}' raised instead of returning a reply: {type(e).__name__}: {e}",
                details=self._details(model, None, PROVIDER_FAILED),
            )

        if reply.failed:
            error_class = reply.error_class.value if reply.error_class is not None else PROVIDER_FAILED
            return ActionNodeOutput(
                output_text="",
                error_code=error_class,
                error_msg=reply.message,
                details=self._details(model, reply, error_class),
                artifacts=self._failed_call_artifacts(state, prompt),
            )

        reply_text = reply.text or ""
        details = self._details(model, reply, None)
        try:
            artifacts = self._audit_artifacts(state, prompt, reply_text) if self.record else {}
        except OSError as e:
            return ActionNodeOutput(
                output_text=reply_text,
                error_code=LLM_RECORD_FAILED,
                error_msg=f"The call was answered but its audit artifacts could not be written: {e}",
                details=details,
            )

        try:
            bound = bind_declared_values(self._raw_values(reply_text), self.declarations, subject="reply")
        except WorkflowInputError as e:
            # The reply stays the output text: what the model actually said is the evidence an author
            # needs to see, and a guard may route on it. See ADR 014 §1.
            return ActionNodeOutput(
                output_text=reply_text,
                error_code=LLM_ANSWER_INVALID,
                error_msg=str(e),
                details=details,
                artifacts=artifacts,
            )
        return ActionNodeOutput(
            output_text=reply_text, param_writes=bound.param_writes, details=details, artifacts=artifacts
        )
