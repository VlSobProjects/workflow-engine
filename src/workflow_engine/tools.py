from collections.abc import Callable, Mapping

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
