from dataclasses import dataclass
from typing import Self, cast

from workflow_engine.exceptions import WorkflowError
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
    get_and_check_registered,
    get_registered_transaction,
)
from workflow_engine.transition.base import BaseTransaction, WithErrors, WithNextNode
from workflow_engine.validators.output_validators import (
    BaseOutputValidator,
    validator_factory,
)
from workflow_engine.workflow import WorkflowNode, stop_on_error_node_factory


@dataclass
class NextTransition(WithNextNode):
    def transition(self, output: ActionNodeOutput, state: StateModel, workflow_nodes: set[str]) -> str | None:
        self.check_error(workflow_nodes)
        return self.next_node

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        return cls(next_node=cls.get_next_node_value(data))

    @classmethod
    def is_on_error(cls) -> bool:
        return False


@dataclass
class ValidatorBasedTransition(WithNextNode):
    validator: BaseOutputValidator

    def transition(self, output: ActionNodeOutput, state: StateModel, workflow_nodes: set[str]) -> str | None:
        self.check_error(workflow_nodes)
        return self.next_node if self.validator.validate_output(output.output_text, state) else None

    @classmethod
    def from_validator(cls, next_node: str, validator: BaseOutputValidator) -> Self:
        return cls(next_node=next_node, validator=validator)

    @classmethod
    def is_on_error(cls) -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        cls.validate_keys(data)
        next_node = data["next"]
        validator_dict = data["validator"]
        if not isinstance(next_node, str):
            raise TypeError(f"Expected 'next' is 'str', got '{type(next_node).__name__}'")
        if not isinstance(validator_dict, dict):
            raise TypeError(f"Expected 'validator' is 'dict', got '{type(validator_dict).__name__}'")

        validator = validator_factory(validator_dict)
        if validator is None:
            raise ValueError(f"Failed to create validator from: {validator_dict}")

        return cls(next_node=next_node, validator=validator)

    @classmethod
    def data_keys(cls) -> list[str]:
        return WithNextNode.data_keys() + ["validator"]


@dataclass
class NextOnErrorTransition(WithNextNode, WithErrors):
    def transition(self, output: ActionNodeOutput, state: StateModel, workflow_nodes: set[str]) -> str | None:
        self.check_error(workflow_nodes)
        if self.is_error(output):
            return self.next_node
        else:
            return None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        return cls(
            next_node=cls.get_next_node_value(data), errors=cls.get_errors(data), attempts=cls.get_attempts_value(data)
        )

    @classmethod
    def data_keys(cls) -> list[str]:
        return WithNextNode.data_keys() + WithErrors.data_keys()


@dataclass
class StopOnErrorTransition(WithErrors):
    """Transition to stop workflow on not recoverable errors."""

    def check_error(self, workflow_nodes: set[str]):
        pass

    def transition(self, output: ActionNodeOutput, state: StateModel, workflow_nodes: set[str]) -> str | None:
        if output.error_code and self.is_error(output):
            return stop_on_error_node_factory(f"Stop on error transition - {output.on_error()}")
        return None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        return cls(errors=cls.get_errors(data), attempts=cls.get_attempts_value(data))


@dataclass
class FunctionTransition(BaseTransaction):
    registered_transaction: RegisteredFunctionExecutor[str | None]
    parameters: dict[str, object]

    @classmethod
    def is_on_error(cls) -> bool:
        return False

    def check_error(self, workflow_nodes: dict[str, WorkflowNode]):
        pass

    @classmethod
    def data_keys(cls) -> list[str]:
        return [FUNCTION_NAME_KEY]

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        cls.validate_keys(data)
        params: dict[str, object] = (
            cast(dict[str, object], data["parameters"])
            if "parameters" in data and isinstance(data["parameters"], dict)
            else {}
        )
        updated_params = dict(params)
        updated_params.update({"output": "", "state": None, "workflow_nodes": None})
        return cls(
            registered_transaction=get_and_check_registered(get_registered_transaction, data, updated_params),
            parameters=updated_params,
        )

    def transition(
        self, output: ActionNodeOutput, state: StateModel, workflow_nodes: dict[str, WorkflowNode]
    ) -> WorkflowNode | None:
        params = dict(self.parameters)
        params.update({"output": output, "state": state, "workflow_nodes": workflow_nodes})
        node_id = self.registered_transaction.execute(parameters_modified=state.set_parameters_with_updater(params))
        if node_id is not None and node_id not in workflow_nodes:
            raise WorkflowError(f"Node '{node_id}' not found in workflow nodes")
        return workflow_nodes[node_id] if node_id is not None else None

    def validate_next_node(self):
        pass


TRANSITIONS: list[type[BaseTransaction]] = [
    ValidatorBasedTransition,
    NextOnErrorTransition,
    FunctionTransition,
    NextTransition,
    StopOnErrorTransition,
]


def transition_factory(data: dict[str, object]) -> BaseTransaction:
    for transition_cls in TRANSITIONS:
        if transition_cls.is_class(data):
            return transition_cls.from_dict(data)
    raise ValueError(f"Invalid transition data: {data}")
