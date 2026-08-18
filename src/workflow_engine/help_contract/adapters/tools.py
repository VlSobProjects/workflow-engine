"""Shared helpers for normalizing registrations into help DTOs."""

import inspect
from typing import Annotated, Final, get_args, get_origin

from workflow_engine.help_contract.models import HelpParameter
from workflow_engine.registry.function_registry import RegisteredFunction, RegisteredValidator

# Parameter names the engine fills in itself when calling a function or a validator.
# They are not node configuration keys and are excluded from operator parameters.
ENGINE_PROVIDED_PARAMS: Final[tuple[str, ...]] = ("state", "output", "action_output")

_DOC_SECTION_HEADERS: Final[tuple[str, ...]] = ("args:", "returns:", "raises:", "yields:", "examples:")


def unwrap_annotation(annotation: object) -> tuple[object, str]:
    """Split an annotation into its base type and the Annotated string metadata, if any."""
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        base = args[0]
        for metadata in args[1:]:
            if isinstance(metadata, str):
                return base, metadata
        return base, ""
    return annotation, ""


def type_display(annotation: object) -> str:
    """A display string of a type annotation for operator help payloads."""
    if annotation is inspect.Parameter.empty or annotation is None:
        return "any"
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation).replace("typing.", "")


def split_docstring(doc: str | None) -> tuple[str, dict[str, str]]:
    """Split a docstring into the narrative text and the entries of its ``Args`` section."""
    if not doc:
        return "", {}
    narrative_lines: list[str] = []
    args: dict[str, str] = {}
    in_args = False
    current_name: str | None = None
    for raw_line in doc.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if lowered == "args:":
            in_args = True
            current_name = None
            continue
        if lowered in _DOC_SECTION_HEADERS:
            in_args = False
            current_name = None
            continue
        if in_args:
            name, separator, description = line.partition(":")
            if separator and name and " " not in name.strip():
                current_name = name.strip()
                args[current_name] = description.strip()
            elif current_name is not None and line:
                args[current_name] = f"{args[current_name]} {line}".strip()
        else:
            narrative_lines.append(line)
    narrative = "\n".join(narrative_lines).strip()
    return narrative, args


def get_function_parameters(
    function: RegisteredFunction | RegisteredValidator,
) -> tuple[dict[str, HelpParameter], tuple[str, ...]]:
    """Node-configuration parameters of a registered function, and the engine-provided names.

    Descriptions come from ``Annotated`` string metadata first and from the ``Args`` docstring
    section second. Engine-provided parameters are excluded and reported separately.
    """
    _, doc_args = split_docstring(inspect.getdoc(function.function))
    parameters: dict[str, HelpParameter] = {}
    engine_provided: list[str] = []
    for name, param in function.signature.parameters.items():
        if name in ENGINE_PROVIDED_PARAMS:
            engine_provided.append(name)
            continue
        base, annotated_description = unwrap_annotation(param.annotation)
        description = annotated_description or doc_args.get(name, "")
        parameters[name] = HelpParameter(
            type=type_display(base),
            description=description,
            required=param.default is inspect.Parameter.empty,
        )
    return parameters, tuple(engine_provided)


def get_function_description(function: RegisteredFunction | RegisteredValidator) -> str:
    """The operator description of a registered function: docstring narrative, else the summary."""
    narrative, _ = split_docstring(inspect.getdoc(function.function))
    return narrative or function.summary or ""
