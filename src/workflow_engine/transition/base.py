from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self

from workflow_engine.engine import is_workflow_node
from workflow_engine.models.state import StateModel


@dataclass
class BaseTransaction(ABC):
    next_node: str

    @abstractmethod
    def get_next_node_id(self,output:str, stat: StateModel) -> str | None:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        pass

    @classmethod
    @abstractmethod
    def data_keys(cls) -> list[str]:
        pass

    @classmethod
    def validate_keys(cls, data: dict[str, object]) -> None:
        missing_keys = []
        for key in cls.data_keys():
            if key not in data:
                missing_keys.append(key)
        if missing_keys:
            raise ValueError(f"Missing keys: {missing_keys}")

    def validate_next_node(self):
        if not is_workflow_node(self.next_node):
            raise ValueError(f"Next node: '{self.next_node}' not exist in workflow")