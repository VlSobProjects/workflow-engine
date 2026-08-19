"""Parsing and codec-decoding of operator input assignments. See ADR 012.

The CLI use-case layer splits each ``--input NAME[:TYPE]=VALUE`` occurrence into an ``InputAssignment``;
the engine decodes it against the workflow's declared ``inputs`` and binds the typed value. Both sides
depend on this domain module rather than on each other.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from workflow_engine.exceptions import WorkflowConfigurationError, WorkflowInputError
from workflow_engine.models.workflow import InputDeclaration
from workflow_engine.registry.type_registry import Codec, resolve_codec_by_type_name


@dataclass(frozen=True)
class InputAssignment:
    """One parsed ``--input`` occurrence: the input name, an optional explicit codec type, and the value text."""

    name: str
    type: str | None
    value: str


def parse_input_assignment(raw: str) -> InputAssignment:
    """Split ``NAME[:TYPE]=VALUE`` into its parts. See ADR 012.

    The first ``=`` separates the value (which may itself contain ``=``, ``:``, spaces and JSON); the first
    ``:`` in the left part separates the optional type from the name. An assignment without ``=`` is an error.
    """
    name_type, sep, value = raw.partition("=")
    if sep == "":
        raise WorkflowInputError(f"Invalid input assignment '{raw}': expected NAME[:TYPE]=VALUE")
    name, colon, type_name = name_type.partition(":")
    return InputAssignment(name=name, type=type_name if colon else None, value=value)


def _resolve_codec(type_name: str, input_name: str) -> type[Codec]:
    try:
        return resolve_codec_by_type_name(type_name)
    except WorkflowConfigurationError as exc:
        raise WorkflowInputError(f"input '{input_name}': {exc}") from exc


def resolve_input_codec(assignment: InputAssignment, declaration: InputDeclaration) -> type[Codec] | None:
    """Resolve the codec by precedence: explicit assignment type, else the declared type, else none.

    When both an explicit and a declared type are present they must resolve to the same codec.
    """
    explicit = _resolve_codec(assignment.type, assignment.name) if assignment.type is not None else None
    declared = _resolve_codec(declaration.type, assignment.name) if declaration.type is not None else None
    if explicit is not None and declared is not None and explicit is not declared:
        raise WorkflowInputError(
            f"input '{assignment.name}': explicit type '{assignment.type}' disagrees with the "
            f"declared type '{declaration.type}'"
        )
    return explicit or declared


def decode_declared_value(
    name: str, value: object, codec: type[Codec] | None, subject: str = "input"
) -> tuple[object, str | None]:
    """Decode an already-parsed value by its declared codec, into the value and the full codec name.

    This is the codec half of the binding rule, reached by both callers: the ``--input`` string transport
    below, and a JSON answer whose values are typed already (ADR 013 §4). A name declared without a type
    is bound as given. A codec that cannot decode the value is an error, reported against ``subject``.
    """
    if codec is None:
        return value, None
    try:
        decoded = codec.value_from_dict_obj(value)
    except Exception as exc:
        raise WorkflowInputError(f"{subject} '{name}': cannot decode value as {codec.type_name()}: {exc}") from exc
    return decoded, codec.type_name()


def decode_input_value(assignment: InputAssignment, declaration: InputDeclaration) -> tuple[object, str | None]:
    """Decode an assignment into its typed Python value and the resolved full codec name (or ``None``).

    An untyped value is bound as the literal string. A typed value is parsed as JSON, falling back to the
    raw string when it is not valid JSON, then decoded by the codec. That parse-or-fall-back step belongs
    to the command-line string transport alone; the decoding itself is shared. See ADR 012, ADR 013 §4.
    """
    codec = resolve_input_codec(assignment, declaration)
    if codec is None:
        return assignment.value, None
    try:
        parsed = json.loads(assignment.value)
    except json.JSONDecodeError:
        parsed = assignment.value
    return decode_declared_value(assignment.name, parsed, codec)
