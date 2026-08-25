from collections.abc import Iterable, Sized
from pathlib import Path

from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    register_validator,
)
from workflow_engine.tools import render_value_as_text
from workflow_engine.validators.functions_validators import not_empty_str_arg_validator


@register_validator(summary="Output text is a path to an existing file")
def is_output_exist_file(output: str) -> bool:
    """Holds when the output text is a path to an existing file."""
    return Path(output).is_file()


@register_validator(
    summary="A configured path is an existing file",
    decorators=[not_empty_str_arg_validator({"file_path": 0})],
)
def is_file_exist(file_path: str) -> bool:
    """Holds when the configured 'file_path' points to an existing file.

    Args:
        file_path: Path to the file to check.
    """
    return Path(file_path).is_file()


@register_validator(
    summary="Output text contains a configured substring",
    decorators=[not_empty_str_arg_validator({"substring": 1})],
)
def is_output_contains_str(output: str, substring: str) -> bool:
    """Holds when the output text contains the configured substring.

    Args:
        substring: The substring the output text must contain.
    """
    return substring in output


@register_validator(summary="Output text is a path to an existing folder")
def is_output_exist_folder(output: str) -> bool:
    """Holds when the output text is a path to an existing folder."""
    return Path(output).is_dir()


@register_validator(summary="Output text is an integer")
def is_output_number(output: str) -> bool:
    """Holds when the output text is a signed or unsigned integer."""
    if output[0] in ["+", "-"]:
        return bool(output[1:].isdigit())
    return bool(output.isdigit())


@register_validator(summary="A collection parameter holds at least a configured number of items")
def is_collection_size_at_least(
    collection: Sized,
    minimum: int,
) -> bool:
    """Holds when the configured collection holds at least 'minimum' items.

    The counting half of an accumulating loop: a node appends to a list and this routes the run out of
    the loop once enough has been collected. Reversed, it is the transition that keeps the loop going.
    The engine resolves 'param.<name>' before the check, so the collection arrives as the value itself.

    Args:
        collection: The collection to measure, normally a 'param.<name>' reference to a list parameter.
        minimum: The number of items from which the check holds.
    """
    return len(collection) >= minimum


@register_validator(summary="Output text is one of the members of a listed collection")
def is_output_in_collection(
    output: str,
    collection: Iterable[object],
) -> bool:
    """Holds when the output text is one of the members of the configured collection.

    The routing half of a configured list: a parameter names the cases a branch handles - the file
    formats worth describing, the categories worth a second pass - and this sends the run down that
    branch when the node just visited produced one of them. The engine resolves 'param.<name>'
    before the check, so the collection arrives as the value itself.

    A member is compared as the text of the value, by the one rendering rule (ADR 008), so a
    collection of paths compares in POSIX form as everything else does. A single string is compared
    as one member and never letter by letter.

    Args:
        collection: The collection to look in, normally a 'param.<name>' reference to a list parameter.
    """
    members = [collection] if isinstance(collection, str) else collection
    return any(output == render_value_as_text(member) for member in members)


@register_validator(
    summary="A dictionary the node wrote carries only allowed keys and every required one",
    decorators=[not_empty_str_arg_validator({"name": 1})],
)
def is_answer_keys_valid(
    action_output: ActionNodeOutput,
    name: str,
    allowed: Iterable[object] | None = None,
    required: Iterable[object] | None = None,
) -> bool:
    """Holds when the value the node wrote under 'name' is a dictionary whose keys fit the lists.

    The check over a structured answer's shape: a model or an answerer binds a value declared as
    'dict', and the codec accepts any dictionary - this guard is where the declared keys are
    enforced. It reads the pending write of the node being routed, the same surface 'echo_answer'
    reads, because an answered value reaches the state only after the transition is selected. As a
    'validators' entry it fails the node under this guard's own name.

    With 'allowed', every key of the dictionary must be one of the members; with 'required', every
    member must be present as a key; both may be given, either may be a 'param.<name>' reference to
    a list. With neither, the check only demands a dictionary. Keys and members are compared as the
    text of their values, by the one rendering rule (ADR 008). A name the node wrote nothing under,
    or a value that is not a dictionary, does not hold.

    Args:
        name: Name of the written value - an 'answer' declaration of the node - to check.
        allowed: Members the keys must be drawn from, normally a 'param.<name>' reference.
        required: Members that must all be present as keys.
    """
    value = action_output.get_param(name)
    if not isinstance(value, dict):
        return False
    keys = {render_value_as_text(key) for key in value}
    if allowed is not None:
        members = [allowed] if isinstance(allowed, str) else allowed
        if not keys <= {render_value_as_text(member) for member in members}:
            return False
    if required is not None:
        members = [required] if isinstance(required, str) else required
        if any(render_value_as_text(member) not in keys for member in members):
            return False
    return True
