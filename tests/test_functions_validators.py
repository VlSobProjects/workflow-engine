import pytest

from workflow_engine.exceptions import FunctionArgsError
from workflow_engine.output import ActionNodeOutput
from workflow_engine.validators.functions_validators import (
    file_exists_arg_validator,
)


@file_exists_arg_validator({"file_path": 0, "other_param": 1, "another_param": 3})
def function_with_params(file_path: str, other_param: str, number: int, another_param: str) -> ActionNodeOutput:
    print(
        f"Function called with file_path={file_path}, other_param={other_param}, "
        f"number={number}, another_param={another_param}"
    )
    return ActionNodeOutput(output_text="all good")


def test_action_param_file_exists_validator(tests_dir):

    # assert test1.error_code == "file_not_found"
    with pytest.raises(FunctionArgsError) as e:
        _ = function_with_params(file_path="path/to/file", other_param="value", another_param="value", number=1)
        print(f"FunctionArgsError: {e.value}")

    with pytest.raises(FunctionArgsError) as e:
        _ = function_with_params(str(tests_dir / "test_functions_validators.py"), "value", 1, "value")
        print(f"FunctionArgsError: {e.value}")
    # assert test2.error_code == "file_not_found"
    test3 = function_with_params(
        number=1,
        file_path=str(tests_dir / "test_functions_validators.py"),
        other_param=str(tests_dir / "test_json_storage.py"),
        another_param=str(tests_dir / "test_guards.py"),
    )
    print(f"Test 3: {test3.output_text}, error_code: {test3.error_code}, error_message: {test3.error_message}")
    assert test3.output_text == "all good"
