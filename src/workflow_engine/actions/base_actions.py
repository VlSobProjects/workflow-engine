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
    def execute(self,state: StateModel)->str | None:
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

    def execute(self, state: StateModel) -> ActionNodeOutput | None:
        return self.registered_function.execute(parameters_modified=state.set_parameters)

    @classmethod
    def get_registered_function(cls, data: dict[str, object])-> RegisteredFunctionExecutor[ActionNodeOutput]:
        return get_and_check_registered(get_registered_function, data)





# @register_action
# class FunctionAction(BaseAutomaticAction):
#     EXECUTION_MODE = ExecutionMode.AUTOMATIC
#     ACTION_TYPE = 'function'
#
#
#     def execute(self, state: StateModel) -> str | None:
#         pass
#
#
#     @classmethod
#     def from_dict(cls, data: dict[str, object]) -> Self:
#         pass




# @register_action
# @dataclass
# class CopyFileAction(BaseAutomaticAction):
#     EXECUTION_MODE = ExecutionMode.AUTOMATIC
#     ACTION_TYPE = 'copy'
#     path_from: str
#     path_to: str
#
#     def execute(self, state: StateModel) -> str | None:
#         pass
#
#     def validate(self) -> None:
#         errors = []
#         if not self.is_path_from_valid():
#             errors.append(f"Invalid path_from: {self.path_from}")
#
#         if not self.is_path_to_valid():
#             errors.append(f"Invalid path_to: {self.path_to}")
#
#         if len(errors) != 0:
#             raise ActionConfigError(", ".join(errors))
#
#
#     def is_path_from_valid(self) -> bool:
#         return (self.path_from.startswith("param.") or
#                 self.path_from.startswith("output.") or
#                 Path(self.path_from).is_file())
#
#     def is_path_to_valid(self) -> bool:
#         return (self.path_to.startswith("param.") or
#                 self.path_to.startswith("output.") or
#                 Path(self.path_to).is_file())
#
#
#     @classmethod
#     def from_dict(cls, data: dict[str, object]) -> CopyFileAction:
#         path_from = data.get("path_from")
#         if not isinstance(path_from, str):
#             raise ActionConfigError("'path_from' must be string")
#
#         path_to = data.get("path_to")
#         if not isinstance(path_to, str):
#             raise ActionConfigError("'path_to' must be string")
#
#         return cls(
#             path_from=path_from,
#             path_to=path_to,
#         )