from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from workflow_engine.models.state import StateModel
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
    get_and_check_registered,
    get_registered_validator,
)


#TODO idea 1: validator take output as ActionNodeOutput and set in output error validation_error and message what validation is failed.
# Add filed description - to show to the user/agent what was validated in error output.
# If implement it need to be work out CombinedOutputValidator to set in output block which case validator failed or description for all CombinedOutputValidator.
# ides 2: set error code for evry validator - 1. transition can use it to transit to the next node 2. CombinedOutputValidator will get last error code and and use it to fiend error description
class BaseOutputValidator(ABC):
    reversed: bool = False
    
    def __init__(self,data: dict[str, object]):
        if "reversed" in data:
            r = data["reversed"]
            if isinstance(r, bool):
                self.reversed = r
    
    @abstractmethod
    def _validate_output(self, output: str, state: StateModel)->bool:
        pass
    
    def validate_output(self, output: str, state: StateModel)->bool:
        result = self._validate_output(output, state)
        if self.reversed:
            return not result
        return result

    @classmethod
    @abstractmethod
    def data_keys(cls) -> list[str]:
        pass

    @classmethod
    def validate_keys(cls, data: dict[str, object]) -> None:
        if cls.is_class(data):
            return
        missing_keys = []
        for key in cls.data_keys():
            if key not in data:
                missing_keys.append(key)
        if missing_keys:
            raise ValueError(f"Missing keys: {missing_keys}")

    @classmethod
    def is_class(cls, data: dict[str, object]) -> bool:
        for key in cls.data_keys():
            if key not in data:
                return False
        return True


class OutputValueValidator(BaseOutputValidator,ABC):
    value: str
    
    def __init__(self,data: dict[str, object]):
        super().__init__(data)
        value = data[self.data_keys()[0]]
        if not isinstance(value, str):
            raise TypeError(f"'value' must be a string found {type(value).__name__}")
        self.value = value

    def converted_value(self,state: StateModel)->str:
        return state.set_parameters({"value":self.value})["value"].__str__()




class OutputContainsValidator(OutputValueValidator):

    def __init__(self,data: dict[str, object]):
        super().__init__(data)

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["contains"]

    def _validate_output(self, output: str, state: StateModel) -> bool:
        return self.converted_value(state) in output

class OutputEqualsValidator(OutputValueValidator):

    def __init__(self,data: dict[str, object]):
        super().__init__(data)

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["equals"]

    def _validate_output(self, output: str, state: StateModel) -> bool:
        return self.converted_value(state) == output

class OutputStartWithValidator(OutputValueValidator):
    def __init__(self,data: dict[str, object]):
        super().__init__(data)

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["starts_with"]

    def _validate_output(self, output: str, state: StateModel) -> bool:
        return output.startswith(self.converted_value(state))

class OutputEndWithValidator(OutputValueValidator):
    def __init__(self,data: dict[str, object]):
        super().__init__(data)

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["ends_with"]

    def _validate_output(self, output: str, state: StateModel) -> bool:
        return output.endswith(self.converted_value(state))

class Combiner(Enum):
    OR = "or"
    AND = "and"

    @classmethod
    def from_dict(cls, validator_dict: dict[str,object]) -> "Combiner":
        if cls.dict_key() in validator_dict:
            value = validator_dict[cls.dict_key()]
            if isinstance(value, str) and value.lower() == "or":
                return Combiner.OR
        return Combiner.AND

    @classmethod
    def dict_key(cls) -> str:
        return "operator"


@dataclass
class ValidatorCombiner:
    validator: BaseOutputValidator
    combiner: Combiner

    def combine(self, prev_validator_function: Callable[[str, StateModel], bool] | None=None) -> Callable[[str, StateModel], bool]:
        if prev_validator_function is None:
            return lambda output,state: self.validator.validate_output(output, state)
        if self.combiner == Combiner.AND:
            return lambda output,state: prev_validator_function(output, state) and self.validator.validate_output(output, state)
        else:
            return lambda output,state: prev_validator_function(output, state) or self.validator.validate_output(output, state)


@dataclass
class CombinedOutputValidator(BaseOutputValidator):
    validators: list[ValidatorCombiner]

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        combiners: list[ValidatorCombiner] = []
        validators = data["validators"]
        if not isinstance(validators, list):
            raise TypeError(f"'validators' must be a list found {type(validators).__name__}")
        for validator_dict in validators:
            if isinstance(validator_dict, dict):
                validator = validator_factory(validator_dict)
                if validator is not None:
                    combiners.append(ValidatorCombiner(validator=validator,combiner=Combiner.from_dict(validator_dict)))
        if not len(combiners) > 0:
            raise ValueError("Combined Output Validator 'validators' must contain at least one valid validator")
        self.validators = combiners

    def _validate_output(self, output: str, state: StateModel) -> bool:
        next_validator_function = None
        for validator in self.validators:
            next_validator_function = validator.combine(next_validator_function)
        if next_validator_function is None:
            raise ValueError("Combined Output Validator 'validators' must be not empty")
        return next_validator_function(output, state)

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["validators"]



class OutputFunctionValidator(BaseOutputValidator):
    registered_validator: RegisteredFunctionExecutor[bool]

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.registered_validator = get_and_check_registered(get_registered_validator,data,{"output":""})

    @classmethod
    def data_keys(cls) -> list[str]:
        return [FUNCTION_NAME_KEY]

    def _validate_output(self, output: str, state: StateModel) -> bool | None:
        return self.registered_validator.execute(parameters_modified=state.set_parameters_with_updater({"output": output,"state":state}))

VALIDATOR_CLASSES: list[type[BaseOutputValidator]] = [
    OutputContainsValidator,
    OutputEqualsValidator,
    OutputStartWithValidator,
    OutputEndWithValidator,
    OutputFunctionValidator,
    CombinedOutputValidator,
]


def validator_factory(data: dict[str, object]) -> BaseOutputValidator:
    for v_class in VALIDATOR_CLASSES:
        if v_class.is_class(data):
            return v_class(data)
    raise ValueError(f"Failed to create validator from: {data}")