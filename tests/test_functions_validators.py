import pytest

from workflow_engine.exceptions import FunctionRuntimeError
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
    with pytest.raises(FunctionRuntimeError) as e:
        _ = function_with_params(file_path="path/to/file", other_param="value", another_param="value", number=1)
        print(f"FunctionRuntimeError: {e.value}")

    with pytest.raises(FunctionRuntimeError) as e:
        _ = function_with_params(
            file_path=(tests_dir / "test_functions_validators.py").as_posix(),
            other_param="value",
            number=1,
            another_param="value",
        )
        print(f"FunctionRuntimeError: {e.value}")
    # assert test2.error_code == "file_not_found"
    test3 = function_with_params(
        number=1,
        file_path=(tests_dir / "test_functions_validators.py").as_posix(),
        other_param=(tests_dir / "test_json_storage.py").as_posix(),
        another_param=(tests_dir / "test_guards.py").as_posix(),
    )
    print(f"Test 3: {test3.output_text}, error_code: {test3.error_code}, error_message: {test3.error_msg}")
    assert test3.output_text == "all good"


def test_validator_failure_reads_as_a_message_not_as_a_parameter_dump():
    """The failure text belongs in the message; the parameters slot reports the call, not the fault."""
    with pytest.raises(FunctionRuntimeError) as error:
        function_with_params(file_path="path/to/file", other_param="value", another_param="value", number=1)

    message = str(error.value)
    assert message.startswith("Function runtime error in 'function_with_params': ")
    assert "file_path: Argument path/to/file - validation 'file exists' failed." in message
    assert "with parameters" not in message
    assert "No message" not in message
