from pathlib import Path

from workflow_engine.registry.function_registry import register_validator


@register_validator
def is_output_exist_file(output: str) -> bool:
    """checking if output is an existing file"""
    return Path(output).is_file()

@register_validator
def is_output_contains_str(output: str, substring: str) -> bool:
    """checking if output contains a specific string"""
    return substring in output

@register_validator
def is_output_number(output: str) -> bool:
    """checking if output is a sign or unsign Integer"""
    if output[0] in ["+", "-"]:
        return bool(output[1:].isdigit())
    return bool(output.isdigit())




