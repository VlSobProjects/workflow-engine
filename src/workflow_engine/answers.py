"""The interactive exchange: the question a paused node publishes and the answer that resumes it.

Two directions of one contract. See ADR 013.

- ``question_block`` reduces a presentation into the caller-facing document of a paused interactive
  node. It is the published shape, not ``PresentResponse``: the same class also carries setup errors,
  budget stops, node failures and completion, none of which belong in the command contract.
- ``parse_answer`` and ``bind_answer`` turn a caller's JSON answer into the node output the engine
  routes through the node's own guards and transitions.

Refusing an answer is a command error: nothing is applied and nothing is journaled, so the domain
layer raises rather than returning a partial result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from workflow_engine.actions.action_present import AnswerContract, PresentResponse
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.exceptions import WorkflowAnswerError, WorkflowConfigurationError, WorkflowInputError
from workflow_engine.inputs import decode_declared_value
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.type_registry import Codec, resolve_codec_by_type_name

ANSWER_FAILED = "answer_failed"
"""The generic failure code every interactive node accepts beside its own catalogue."""

UNSPECIFIED_ACTOR = "unspecified"

_ANSWER_KEYS = frozenset({"status", "values", "text", "error_code", "message", "actor"})


class AnswerStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class Answer:
    """One answer to a paused interactive node, as supplied by whoever answered. See ADR 013 §4."""

    status: AnswerStatus
    values: dict[str, object] = field(default_factory=dict)
    text: str = ""
    error_code: str | None = None
    message: str | None = None
    actor: str = UNSPECIFIED_ACTOR


@dataclass(frozen=True)
class BoundAnswer:
    """A validated answer: the node output it becomes, and the codecs its values were decoded by.

    The codecs travel separately because the journal records the names and their types, never the
    values, mirroring ``inputs_set``.
    """

    output: ActionNodeOutput
    codecs: dict[str, str | None]


def _string_field(data: dict[str, object], key: str, default: str | None) -> str | None:
    value = data.get(key, default)
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkflowAnswerError(f"answer field '{key}' must be a string")
    return value


def parse_answer(raw: str) -> Answer:
    """Parse the answer document. Every shape error is a refusal, never a silent default.

    Unknown top-level keys are refused too: a caller that misspells ``values`` must learn it here
    rather than have the answer bind nothing and route as if it had answered.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkflowAnswerError(f"answer is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkflowAnswerError("answer must be a JSON object")
    unknown = sorted(set(data) - _ANSWER_KEYS)
    if unknown:
        raise WorkflowAnswerError(f"unknown answer field(s) {unknown}; known fields: {sorted(_ANSWER_KEYS)}")

    raw_status = data.get("status")
    try:
        status = AnswerStatus(raw_status)
    except ValueError as exc:
        allowed = [member.value for member in AnswerStatus]
        raise WorkflowAnswerError(f"answer field 'status' must be one of {allowed}, got {raw_status!r}") from exc

    values = data.get("values", {})
    if not isinstance(values, dict):
        raise WorkflowAnswerError("answer field 'values' must be an object of declared name to value")

    actor = _string_field(data, "actor", UNSPECIFIED_ACTOR)
    if not actor:
        raise WorkflowAnswerError("answer field 'actor' must not be empty")

    answer = Answer(
        status=status,
        values=dict(values),
        text=_string_field(data, "text", "") or "",
        error_code=_string_field(data, "error_code", None),
        message=_string_field(data, "message", None),
        actor=actor,
    )
    if status is AnswerStatus.FAILURE and answer.error_code is None:
        raise WorkflowAnswerError("a failure answer must carry an 'error_code'")
    if status is AnswerStatus.SUCCESS and answer.error_code is not None:
        raise WorkflowAnswerError("a success answer must not carry an 'error_code'")
    if status is AnswerStatus.FAILURE and answer.values:
        raise WorkflowAnswerError("a failure answer answered nothing and must not carry 'values'")
    return answer


def load_answer(raw: str | None, path: str | None) -> Answer | None:
    """Read the answer from whichever transport carries it, or ``None`` when the caller sent none.

    An absent answer is not an error: at a paused interactive node it re-presents the same question
    (ADR 013 §6), and everywhere else the resume simply carries nothing.
    """
    if raw is not None and path is not None:
        raise WorkflowAnswerError("an answer is supplied either inline or as a file, not both")
    if raw is not None:
        return parse_answer(raw)
    if path is None:
        return None
    answer_file = Path(path)
    try:
        content = answer_file.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise WorkflowAnswerError(f"cannot read answer file '{answer_file.as_posix()}': {exc}") from exc
    return parse_answer(content)


def _declared_codec(name: str, type_name: str | None) -> type[Codec] | None:
    if type_name is None:
        return None
    try:
        return resolve_codec_by_type_name(type_name)
    except WorkflowConfigurationError as exc:
        raise WorkflowAnswerError(f"answer '{name}': {exc}") from exc


def bind_answer(answer: Answer, contract: AnswerContract) -> BoundAnswer:
    """Validate an answer against the node's declaration and turn it into the node's output.

    A success binds every declared value as a ``SET`` write: an answer is a value, not an operation on
    the bus. Overwriting is allowed because a question asked again in a loop answers the same names.
    A failure produces an output carrying its error code, which the node's own transitions route.
    """
    declared = {declaration.name: declaration for declaration in contract.declarations}
    undeclared = sorted(set(answer.values) - set(declared))
    if undeclared:
        raise WorkflowAnswerError(f"undeclared answer name(s) {undeclared}; declared: {sorted(declared)}")

    if answer.status is AnswerStatus.FAILURE:
        allowed = contract.declared_codes() | {ANSWER_FAILED}
        if answer.error_code not in allowed:
            raise WorkflowAnswerError(
                f"error code '{answer.error_code}' is not declared by the node; allowed: {sorted(allowed)}"
            )
        return BoundAnswer(
            output=ActionNodeOutput(output_text=answer.text, error_code=answer.error_code, error_msg=answer.message),
            codecs={},
        )

    missing = sorted(
        declaration.name
        for declaration in contract.declarations
        if declaration.required and declaration.name not in answer.values
    )
    if missing:
        raise WorkflowAnswerError(f"missing required answer name(s) {missing}")

    param_writes: dict[str, ParamWrite] = {}
    codecs: dict[str, str | None] = {}
    for name, value in answer.values.items():
        declaration = declared[name]
        try:
            decoded, codec_name = decode_declared_value(
                name, value, _declared_codec(name, declaration.type), subject="answer"
            )
        except WorkflowAnswerError:
            raise
        except WorkflowInputError as exc:
            raise WorkflowAnswerError(str(exc)) from exc
        param_writes[name] = ParamWrite(mode=WriteParamMode.SET, value=decoded, allow_overwrite=True)
        codecs[name] = codec_name
    return BoundAnswer(output=ActionNodeOutput(output_text=answer.text, param_writes=param_writes), codecs=codecs)


def question_block(node_id: str, response: PresentResponse) -> dict[str, object]:
    """The caller-facing document of a paused interactive node: the question and how to answer it.

    Optional presentation fields appear only when the node set them, so the block states what the
    author wrote and nothing else. See ADR 013 §3.
    """
    contract = response.answer or AnswerContract()
    block: dict[str, object] = {
        "node_id": node_id,
        "title": response.title,
        "description": response.description,
        "instruction": response.instruction,
        "answer": [declaration.to_dict() for declaration in contract.declarations],
        "error_catalogue": dict(contract.error_catalogue),
        "generic_error_code": ANSWER_FAILED,
    }
    optional: dict[str, object | None] = {
        "goal": response.goal,
        "context": response.context,
        "options": response.options,
        "requirements": response.requirements,
        "constraints": response.constraints,
        "examples": response.examples,
        "hints": response.hints,
    }
    block.update({key: value for key, value in optional.items() if value is not None})
    return block
