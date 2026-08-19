from collections.abc import Sized
from pathlib import Path

from workflow_engine.registry.function_registry import (
    register_validator,
)
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
