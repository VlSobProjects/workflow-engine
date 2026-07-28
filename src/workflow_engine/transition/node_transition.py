from dataclasses import dataclass
from typing import Self

from workflow_engine.models.state import StateModel
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
    get_and_check_registered,
    get_registered_transaction,
)
from workflow_engine.transition.base import BaseTransaction
from workflow_engine.validators.output_validators import BaseOutputValidator, factory


@dataclass
class NextTransition(BaseTransaction):
    next_node: str

    def get_next_node_id(self, output: str, stat: StateModel) -> str | None:
        self.validate_next_node()
        return self.next_node

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        cls.validate_keys(data)
        value = data['next']
        if not isinstance(value, str):
            raise TypeError(f"Expected 'next' is 'str', got '{type(value).__name__}'")

        return cls(next_node=value)

    @classmethod
    def data_keys(cls) -> list[str]:
        return ['next']

@dataclass
class ValidatorBasedTransition(BaseTransaction):
    next_node: str
    validator: BaseOutputValidator

    def get_next_node_id(self, output: str, stat: StateModel) -> str | None:
        self.validate_next_node()
        return self.next_node if self.validator.validate_output(output, stat) else None

    @classmethod
    def from_validator(cls, next_node: str, validator: BaseOutputValidator) -> Self:
        return cls(next_node=next_node, validator=validator)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        cls.validate_keys(data)
        next_node = data['next']
        validator_dict = data['validator']
        if not isinstance(next_node, str):
            raise TypeError(f"Expected 'next' is 'str', got '{type(next_node).__name__}'")
        if not isinstance(validator_dict, dict):
            raise TypeError(f"Expected 'validator' is 'dict', got '{type(validator_dict).__name__}'")

        validator = factory(validator_dict)
        if validator is None:
            raise ValueError(f"Failed to create validator from: {validator_dict}")

        return cls(next_node=next_node, validator=validator)

    @classmethod
    def data_keys(cls) -> list[str]:
        return ['next','validator']

@dataclass
class FunctionBasedTransition(BaseTransaction):
    next_node = "dynamic"
    registered_transaction: RegisteredFunctionExecutor[str | None]

    @classmethod
    def data_keys(cls) -> list[str]:
        return [FUNCTION_NAME_KEY]

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        cls.validate_keys(data)
        return cls(registered_transaction=get_and_check_registered(get_registered_transaction, data, {"output": "", "state": None}), next_node ="dynamic")

    def get_next_node_id(self, output: str, stat: StateModel) -> str | None:
        return self.registered_transaction.execute(parameters_modified=stat.set_parameters_with_updater({'output': output, 'state': stat}))

    def validate_next_node(self):
        pass

class StopOnErrorTransition(FunctionBasedTransition):
    """Transition to stop workflow on not recoverable errors."""
    @classmethod
    def data_keys(cls) -> list[str]:
        keyes = super().data_keys()
        keyes.append("errors")
        return keyes