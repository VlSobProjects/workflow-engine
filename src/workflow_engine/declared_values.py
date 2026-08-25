"""Binding declared values into typed parameter writes: one path, two transports. See ADR 014 §1.

The ADR 013 declaration says which names a reply must carry and how they are typed. Two transports
deliver such values: the answer document of whoever answered a paused interactive node, and the
reply of a model call read by the ``llm`` action. Turning them into writes is one code path, so the
two declarations cannot drift apart.

What stays with the caller is what actually differs: how the raw values are extracted from the
transport — a JSON answer document, a reply read by its ``format`` — and what a refusal becomes
there. A refused answer is a command error that applies nothing; a reply that does not fit its
declaration is a routable error value of the node that made the call.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.exceptions import WorkflowConfigurationError, WorkflowInputError
from workflow_engine.inputs import decode_declared_value
from workflow_engine.models.workflow import InputDeclaration
from workflow_engine.output import ParamWrite
from workflow_engine.registry.type_registry import Codec, resolve_codec_by_type_name


@dataclass(frozen=True)
class BoundValues:
    """The writes the declared values became, and the codec name each value was decoded by.

    The codec names travel beside the writes rather than inside them because the journal and the
    record stream carry names and types and never values (ADR 013 §9, ADR 021 §1).
    """

    param_writes: dict[str, ParamWrite]
    codecs: dict[str, str | None]


def _declared_codec(subject: str, name: str, type_name: str | None) -> type[Codec] | None:
    if type_name is None:
        return None
    try:
        return resolve_codec_by_type_name(type_name)
    except WorkflowConfigurationError as exc:
        raise WorkflowInputError(f"{subject} '{name}': {exc}") from exc


def bind_declared_values(
    values: Mapping[str, object], declarations: Sequence[InputDeclaration], subject: str
) -> BoundValues:
    """Validate the supplied values against the declaration and decode them into typed writes.

    Every value is bound as a ``SET`` write: a declared value is a value, not an operation on the
    bus. Overwriting is allowed because a node visited again in a loop produces the same names.

    An undeclared name is refused rather than ignored, so a transport that misspells a name learns
    it here instead of binding nothing and routing as if it had answered. ``subject`` names what is
    being bound in every message, which is the only thing the two callers do not share.
    """
    declared = {declaration.name: declaration for declaration in declarations}
    undeclared = sorted(set(values) - set(declared))
    if undeclared:
        raise WorkflowInputError(f"undeclared {subject} name(s) {undeclared}; declared: {sorted(declared)}")

    missing = sorted(
        declaration.name for declaration in declarations if declaration.required and declaration.name not in values
    )
    if missing:
        raise WorkflowInputError(f"missing required {subject} name(s) {missing}")

    param_writes: dict[str, ParamWrite] = {}
    codecs: dict[str, str | None] = {}
    for name, value in values.items():
        declaration = declared[name]
        decoded, codec_name = decode_declared_value(
            name, value, _declared_codec(subject, name, declaration.type), subject=subject
        )
        param_writes[name] = ParamWrite(mode=WriteParamMode.SET, value=decoded, allow_overwrite=True)
        codecs[name] = codec_name
    return BoundValues(param_writes=param_writes, codecs=codecs)
