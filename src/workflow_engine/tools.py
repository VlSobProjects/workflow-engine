from collections import deque
from collections.abc import Callable, Mapping
from datetime import datetime
from enum import Enum
from pathlib import Path, PurePath

from workflow_engine.exceptions import WorkflowParameterError


def parameter_from_dict[T](
    data: dict[str, object] | Mapping[str, object], param_name: str, expected_type: type[T]
) -> T:
    value = data.get(param_name)
    if value is None:
        raise WorkflowParameterError(param_name, type(value), expected_type, "Parameter not in data or None")

    if not isinstance(value, expected_type):
        raise WorkflowParameterError(param_name, type(value), expected_type, "Parameter type mismatch")
    return value


def parameter_from_dict_with_checker[T](
    data: dict[str, object] | Mapping[str, object],
    param_name: str,
    expected_type: type[T],
    checker: Callable[[T], bool],
    fail_message: str,
) -> T:
    value = data.get(param_name)
    if value is None:
        raise WorkflowParameterError(param_name, type(value), expected_type, "Parameter not in data or None")
    if not isinstance(value, expected_type):
        raise WorkflowParameterError(param_name, type(value), expected_type, "Parameter type mismatch")
    if not checker(value):
        raise WorkflowParameterError(param_name, type(value), expected_type, fail_message)
    return value


def check_param_type[T](param_name: str, expected_type: type[T], param_value: object) -> T:
    if not isinstance(param_value, expected_type):
        raise WorkflowParameterError(param_name, type(param_value), expected_type, "Parameter type mismatch")
    return param_value


def parameter_from_dict_default[T](
    data: dict[str, object] | Mapping[str, object], param_name: str, expected_type: type[T], default_value: T
) -> T:
    value = data.get(param_name)
    if value is None:
        return default_value
    if not isinstance(value, expected_type):
        raise WorkflowParameterError(param_name, type(value), expected_type, "Parameter type mismatch")
    return value


def parameter_from_dict_optional[T](
    data: dict[str, object] | Mapping[str, object], param_name: str, expected_type: type[T]
) -> T | None:
    value = data.get(param_name)
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise WorkflowParameterError(param_name, type(value), expected_type, "Parameter type mismatch")
    return value


def dict_to_text_lv1(title: str, data: dict[str, str], intend: int) -> str:
    spaces = " " * intend
    lines = [f"{spaces}{title}"]
    lines.extend(f"{spaces}    - {k}: {v}" for k, v in data.items())
    return "\n".join(lines)


def dict_to_text_lv2(title: str, data: dict[str, dict[str, str]], intend_start: int, intend: int) -> str:
    start_spaces = " " * intend_start
    lines = [f"{start_spaces}{title}"]
    for k, v in data.items():
        lines.append(dict_to_text_lv1(k, v, intend_start + intend))
    return "\n".join(lines)


def dict_to_text_lv3(title: str, data: dict[str, dict[str, dict[str, str]]], intend_start: int, intend: int) -> str:
    start_spaces = " " * intend_start
    lines = [f"{start_spaces}{title}"]
    for k, v in data.items():
        lines.append(dict_to_text_lv2(k, v, intend_start + intend, intend))
    return "\n".join(lines)


def render_value_as_text(value: object) -> str:
    """Render a state value as the text an engine surface compares, emits or presents.

    One rule for every such surface, and it is the ADR 008 rule: a path renders in POSIX form, on
    every OS. Values reach this point already typed, restored by their codec, so ``str()`` alone would
    put native separators into a guard comparison, a node output and a published document, while the
    same value is stored and serialized as POSIX everywhere else.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, PurePath):
        return value.as_posix()
    return str(value)


def common_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, Path):
        return obj.as_posix()

    if isinstance(obj, Enum):
        return obj.value

    if isinstance(obj, deque):
        return list(obj)

    return None
