from collections.abc import Callable, Mapping

from workflow_engine.exceptions import WorkflowParameterError


def parameter_from_dict[T](data:dict[str,object] | Mapping[str, object],param_name:str, expected_type:type[T]) -> T:
    value = data.get(param_name)
    if value is None:
        raise WorkflowParameterError(param_name, type(value), expected_type,"Parameter not in data or None")

    if not isinstance(value, expected_type):
        raise WorkflowParameterError(param_name, type(value), expected_type,"Parameter type mismatch")
    return value

def parameter_from_dict_with_checker[T](
        data:dict[str,object] | Mapping[str, object],
        param_name:str,
        expected_type:type[T],
        checker: Callable[[T], bool],
        fail_message:str
) -> T:
    value = data.get(param_name)
    if value is None:
        raise WorkflowParameterError(param_name, type(value), expected_type,"Parameter not in data or None")
    if not isinstance(value, expected_type):
        raise WorkflowParameterError(param_name, type(value), expected_type,"Parameter type mismatch")
    if not checker(value):
        raise WorkflowParameterError(param_name, type(value), expected_type, fail_message)
    return value

def check_param_type[T](
        param_name:str,
        expected_type:type[T],
        param_value:object
) -> T:
    if not isinstance(param_value, expected_type):
        raise WorkflowParameterError(param_name, type(param_value), expected_type,"Parameter type mismatch")
    return param_value


def parameter_from_dict_default[T](
        data:dict[str,object] | Mapping[str, object],
        param_name:str,
        expected_type:type[T], default_value:T
) -> T:
    value = data.get(param_name)
    if value is None:
        return default_value
    if not isinstance(value, expected_type):
        raise WorkflowParameterError(param_name, type(value), expected_type,"Parameter type mismatch")
    return value

def parameter_from_dict_optional[T](
        data:dict[str,object] | Mapping[str, object],
        param_name:str,
        expected_type:type[T]
    ) -> T | None:
    value = data.get(param_name)
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise WorkflowParameterError(param_name, type(value), expected_type,"Parameter type mismatch")
    return value
