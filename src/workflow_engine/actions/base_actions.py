from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Self

from workflow_engine.actions.action_present import PresentResponse
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    RegisteredFunctionExecutor,
    get_and_check_registered,
    get_registered_function,
)


class Action(Enum):
    START = "Start"
    ASK_USER_QUESTION = "AskUserQuestion"
    ASK_USER_QUESTIONS = "AskUserQuestions"
    SELECT_OPTION = "SelectOption"
    USER_SELECT_OPTIONS = "UserSelectOptions"
    USER_SUBMIT_FILE= "UserSubmitFile"
    ANALYZE_FILE = "AnalyzeFile"
    COLLECT_REQUIREMENTS = "CollectRequirements"
    GENERATE_PLAN = "GeneratePlan"
    CREATE_UPDATE_FILE="CreateUpdateFile"
    RUN_TOOL="RunTool"
    SUMMARY = "CreateSummary"
    STOP = "Stop"
    STOP_ON_ERROR = "StopOnError"
    RUN_SCRIPT = "RunScript"



class ExecutionMode(Enum):
    AUTOMATIC = auto()
    INTERACTIVE = auto()


class BaseAction(ABC):
    ACTION_TYPE: str
    save_as: str | None = field(default=None)

    def validate_action(self) -> None:
        return

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        pass

    @classmethod
    @abstractmethod
    def execution_mode(cls) -> ExecutionMode:
        pass

@dataclass
class BaseAutomaticAction(BaseAction,ABC):

    @abstractmethod
    def execute(self,state: StateModel)->ActionNodeOutput:
        pass

    @classmethod
    def execution_mode(cls) -> ExecutionMode:
        return ExecutionMode.AUTOMATIC


class BaseInteractiveAction(BaseAction,ABC):

    @abstractmethod
    def present(self,state: StateModel) -> PresentResponse:
        pass

    @classmethod
    def execution_mode(cls) -> ExecutionMode:
        return ExecutionMode.INTERACTIVE

class ActionWithFunction(BaseAutomaticAction,ABC):
    registered_function: RegisteredFunctionExecutor[ActionNodeOutput]

    def execute(self, state: StateModel) -> ActionNodeOutput:
        return self.registered_function.execute(parameters_modified=state.set_parameters)

    @classmethod
    def get_registered_function(cls, data: dict[str, object])-> RegisteredFunctionExecutor[ActionNodeOutput]:
        return get_and_check_registered(get_registered_function, data)
