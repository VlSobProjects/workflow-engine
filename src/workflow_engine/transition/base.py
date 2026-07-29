from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self

from workflow_engine.exceptions import WorkflowError
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.workflow import WorkflowNode


@dataclass
class BaseTransaction(ABC):

    @abstractmethod
    def transition(self, output:ActionNodeOutput, state: StateModel, workflow_nodes:dict[str,WorkflowNode]) -> WorkflowNode | None:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        pass
    
    @classmethod
    @abstractmethod
    def is_on_error(cls) -> bool:
        pass

    @classmethod
    @abstractmethod
    def data_keys(cls) -> list[str]:
        pass

    @abstractmethod
    def check_error(self,workflow_nodes: dict[str, WorkflowNode]):
        pass

    @classmethod
    def validate_keys(cls, data: dict[str, object]) -> None:
        missing_keys = []
        for key in cls.data_keys():
            if key not in data:
                missing_keys.append(key)
        if missing_keys:
            raise ValueError(f"Missing keys: {missing_keys}")

    @classmethod
    def is_class(cls, data: dict[str, object]) -> bool:
        return all(key in data for key in cls.data_keys())

@dataclass
class WithNextNode(BaseTransaction,ABC):
    next_node: str


    @classmethod
    def data_keys(cls) -> list[str]:
        return ['next']

    def check_next_node_id(self,workflow_nodes: dict[str, WorkflowNode])->bool:
        return self.next_node in workflow_nodes

    def check_error(self, workflow_nodes: dict[str, WorkflowNode]):
        if not self.check_next_node_id(workflow_nodes):
            raise WorkflowError(f"Next node '{self.next_node}' not found in workflow nodes")

    @classmethod
    def get_next_node_value(cls, data: dict[str, object]) -> str:
        cls.validate_keys(data)
        value = data['next']
        if not isinstance(value, str):
            raise TypeError(f"Expected 'next' is 'str', got '{type(value).__name__}'")
        return value


@dataclass
class WithErrors(BaseTransaction,ABC):
    errors: list[str]
    attempts: bool

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["errors"]

    @classmethod
    def is_on_error(cls) -> bool:
        return True

    def is_error(self, output:ActionNodeOutput) -> bool:
        return output.error_code is not None and output.error_code in self.errors

    @classmethod
    def get_errors(cls, data: dict[str, object]) -> list[str]:
        cls.validate_keys(data)
        err_list = data['errors']
        if not isinstance(err_list, list):
            raise TypeError(f"Expected 'errors' is 'list', got '{type(err_list).__name__}'")
        if not all(isinstance(err, str) for err in err_list):
            raise TypeError(f"Expected all elements in 'errors' to be 'str', got '{[type(err).__name__ for err in err_list]}'")
        return err_list

    @classmethod
    def get_attempts_value(cls, data: dict[str, object]) -> bool:
        cls.validate_keys(data)
        value = data.get('attempts', False)
        if not isinstance(value, bool):
            raise TypeError(f"Expected 'attempts' is 'bool', got '{type(value).__name__}'")
        return value
