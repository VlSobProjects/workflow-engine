from collections import deque
from collections.abc import Callable

from workflow_engine.collection_param_handlers import (
    INVALID_COLLECTION_STATE,
    INVALID_MODIFY_MODE,
    INVALID_REMOVE_PARAM,
    PARAM_TYPE_MISMATCH,
    ModifyResult,
    WriteParamMode,
    modify_param_object,
)


def chek_result[T](
    t: type[T], error_code: str | None, checker: Callable[[T], bool] | None, collection: object, result: ModifyResult
) -> None:
    assert result.error_code == error_code
    if checker is not None:
        assert checker(result.collection)
    if result.error_code is None:
        assert result.collection != collection
    else:
        assert result.collection == collection
    print("\n", result.__repr__())


def test_update_list():
    target = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    result = modify_param_object(target, "test", WriteParamMode.APPEND, 1)
    chek_result(list, None, lambda x: 1 in x, target, result)
    result = modify_param_object(target, "test", WriteParamMode.REMOVE, "3")
    chek_result(list, None, lambda x: "3" not in x, target, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_LEFT, None)
    chek_result(list, INVALID_MODIFY_MODE, None, target, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_RIGHT, None)
    chek_result(list, INVALID_MODIFY_MODE, None, target, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_INDEX, 1)
    chek_result(list, None, lambda x: "2" not in x, target, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_INDEX, 20)
    chek_result(list, INVALID_COLLECTION_STATE, None, target, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_INDEX, "4")
    chek_result(list, PARAM_TYPE_MISMATCH, None, target, result)
    result = modify_param_object(target, "test", WriteParamMode.REMOVE, "bksdbdjk")
    chek_result(list, INVALID_REMOVE_PARAM, None, target, result)


def test_update_deque():
    target: deque[int] = deque([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    result = modify_param_object(target, "test", WriteParamMode.APPEND, 1)
    chek_result(deque, None, lambda x: 1 in x, target, result)
    result = modify_param_object(target, "test", WriteParamMode.REMOVE, 3)
    chek_result(deque, None, lambda x: 3 not in x, target, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_LEFT, None)
    chek_result(deque, None, lambda x: 1 not in x, target, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_RIGHT, None)
    chek_result(deque, None, lambda x: 10 not in x, target, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_INDEX, 1)
    chek_result(deque, INVALID_MODIFY_MODE, None, target, result)
    d: deque[int] = deque()
    result = modify_param_object(d, "test", WriteParamMode.POP_RIGHT, 20)
    chek_result(deque, INVALID_COLLECTION_STATE, None, d, result)
    result = modify_param_object(target, "test", WriteParamMode.POP_INDEX, 4)
    chek_result(deque, INVALID_MODIFY_MODE, None, target, result)
    result = modify_param_object(target, "test", WriteParamMode.REMOVE, "bksdbdjk")
    chek_result(deque, INVALID_REMOVE_PARAM, None, target, result)
