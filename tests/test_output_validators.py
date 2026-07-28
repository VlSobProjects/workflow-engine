from datetime import datetime
from pathlib import Path

import importlib
import pytest

from workflow_engine.models.state import StateModel, ActionParameter
from workflow_engine.registry.function_registry import FUNCTION_NAME_KEY,FUNCTION_PARAMETERS_KEY
from workflow_engine.validators.output_validators import (
    Combiner,
    factory,
    OutputContainsValidator,
    OutputEqualsValidator,
    OutputStartWithValidator,
    OutputEndWithValidator,
    OutputFunctionValidator,
    CombinedOutputValidator,
    BaseOutputValidator,
)

CONTAINS_VALIDATOR ={"contains": "test_string"}
CONTAINS_VALIDATOR_2 ={"contains": "param.test_param"}
EQUALS_VALIDATOR = {"equals": "test_string"}
EQUALS_VALIDATOR_2 = {"equals": "param.test_param"}
START_WITH_VALIDATOR = {"starts_with": "test_string"}
START_WITH_VALIDATOR_2 = {"starts_with": "param.test_param"}
END_WITH_VALIDATOR = {"ends_with": "test_string"}
END_WITH_VALIDATOR_2 = {"ends_with": "param.test_param"}
OUTPUT_FUNCTION_VALIDATOR_1 = {FUNCTION_NAME_KEY: "is_output_exist_file"}
OUTPUT_FUNCTION_VALIDATOR_2 = {FUNCTION_NAME_KEY: "is_output_contains_str", FUNCTION_PARAMETERS_KEY: {"substring": "param.test_param"}}
COMBINED_OUTPUT_VALIDATOR_1 = {"validators": [CONTAINS_VALIDATOR, {Combiner.dict_key():Combiner.OR.value,"starts_with": "new_test"}]}
COMBINED_OUTPUT_VALIDATOR_2 = {"validators": [EQUALS_VALIDATOR, {Combiner.dict_key():Combiner.OR.value,"ends_with": "new"}, {Combiner.dict_key():Combiner.OR.value,"ends_with": "param.test_param"}]}
COMBINED_OUTPUT_VALIDATOR_3 = {
    "validators":[
        EQUALS_VALIDATOR,
        {"validators": [CONTAINS_VALIDATOR, {Combiner.dict_key():Combiner.AND.value,"starts_with": "new_test"}],Combiner.dict_key():Combiner.OR.value},
        {"validators": [END_WITH_VALIDATOR_2, {Combiner.dict_key():Combiner.OR.value,"starts_with": "param.test_param2"}],Combiner.dict_key():Combiner.OR.value},
    ]
}


VALIDATORS: dict[type[BaseOutputValidator], list[dict[str,object]]] = {
    OutputContainsValidator:[CONTAINS_VALIDATOR,CONTAINS_VALIDATOR_2],
    OutputEqualsValidator:[EQUALS_VALIDATOR, EQUALS_VALIDATOR_2],
    OutputStartWithValidator:[START_WITH_VALIDATOR,START_WITH_VALIDATOR_2],
    OutputEndWithValidator:[END_WITH_VALIDATOR, END_WITH_VALIDATOR_2],
    OutputFunctionValidator:[OUTPUT_FUNCTION_VALIDATOR_1, OUTPUT_FUNCTION_VALIDATOR_2],
    CombinedOutputValidator:[COMBINED_OUTPUT_VALIDATOR_1, COMBINED_OUTPUT_VALIDATOR_2]
}

@pytest.fixture
def register_functions():
    importlib.import_module("workflow_engine.validators.output_function_validators")


@pytest.fixture
def state_base(register_functions):
    return StateModel(
        timestamp=datetime.now(),
        work_dir=Path(""),
        schema_version="1",
        flow_id="test",
        params={
            "test_param": ActionParameter(name="test_param", value="string", source_node_id="test_node_id"),
            "test_param2": ActionParameter(name="test_param2", value="new_string2", source_node_id="test_node_id")
        },
        current_node_id="test_node_id",
    )




def test_factory(register_functions):
    for t,validator_config in  VALIDATORS.items():
        for config in validator_config:
            validator = factory(config)
            assert isinstance(validator, t)
            print(f"validator {validator.__str__()}")



def test_output_contains_validator(state_base):
    validator = factory(CONTAINS_VALIDATOR)
    assert isinstance(validator, OutputContainsValidator)
    assert validator.validate_output("this is a test_string",state_base)
    validator = factory(CONTAINS_VALIDATOR_2)
    assert isinstance(validator, OutputContainsValidator)
    assert validator.validate_output("string",state_base)


def test_output_equals_validator(state_base):
    validator = factory(EQUALS_VALIDATOR)
    assert isinstance(validator, OutputEqualsValidator)
    assert validator.validate_output("test_string", state_base)
    validator = factory(EQUALS_VALIDATOR_2)
    assert isinstance(validator, OutputEqualsValidator)
    assert validator.validate_output("string", state_base)


def test_output_start_with_validator(state_base):
    validator = factory(START_WITH_VALIDATOR)
    assert isinstance(validator, OutputStartWithValidator)
    assert validator.validate_output("test_string in test", state_base)
    validator = factory(START_WITH_VALIDATOR_2)
    assert isinstance(validator, OutputStartWithValidator)
    assert validator.validate_output("string in test", state_base)


def test_output_end_with_validator(state_base):
    validator = factory(END_WITH_VALIDATOR)
    assert isinstance(validator, OutputEndWithValidator)
    assert validator.validate_output("this is a test_string", state_base)
    validator = factory(END_WITH_VALIDATOR_2)
    assert isinstance(validator, OutputEndWithValidator)
    assert validator.validate_output("this is a string", state_base)


def test_combined_output_validator(state_base):
    validator = factory(COMBINED_OUTPUT_VALIDATOR_1)
    assert isinstance(validator, CombinedOutputValidator)
    assert validator.validate_output("new_test is a staring", state_base)
    validator = factory(COMBINED_OUTPUT_VALIDATOR_2)
    assert isinstance(validator, CombinedOutputValidator)
    assert validator.validate_output("this is a string", state_base)
    validator = factory(COMBINED_OUTPUT_VALIDATOR_3)
    assert isinstance(validator, CombinedOutputValidator)
    assert validator.validate_output("new_string2 is a new test", state_base)
    assert not validator.validate_output("new_string is a new test", state_base)


def test_output_function_validator(state_base):
    validator = factory(OUTPUT_FUNCTION_VALIDATOR_1)
    assert isinstance(validator, OutputFunctionValidator)
    assert validator.validate_output("C:\\Users\\Vladimir\\PycharmProjects\\workflow-engine\\src\\workflow_engine\\transition\\transition_functions.py", state_base)
    validator = factory(OUTPUT_FUNCTION_VALIDATOR_2)
    assert isinstance(validator, OutputFunctionValidator)
    assert validator.validate_output("this is a string", state_base)
