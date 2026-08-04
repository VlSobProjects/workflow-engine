from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import field
from datetime import UTC, datetime
from enum import Enum, auto
from pathlib import Path
from typing import cast

from workflow_engine.actions.action_present import PresentResponse
from workflow_engine.exceptions import ActionConfigurationError, WorkflowConfigurationError
from workflow_engine.models.state import StateModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    RegisteredFunctionExecutor,
    get_registered_function,
)


class ExecutionMode(Enum):
    AUTOMATIC = auto()
    INTERACTIVE = auto()

# To pass in get_and_check_registered function as addition_params
# To check action function in configuration stage
# In case action function will have state:StateModel arg so will not accept None
def _factory_sate_stub() ->StateModel:
    return StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=Path("/"),
        schema_version="1",
        flow_id="default",
        current_node_id="start",
        session_id="none"
    )


class BaseAction(ABC):
    ACTION_TYPE: str
    save_as: str | None = field(default=None)

    def __init__(self, data: dict[str, object]):
        if "save_as" in data and isinstance(data["save_as"], str):
            self.save_as = cast(str, data["save_as"])

    def validate_action(self) -> None:
        return

    @classmethod
    @abstractmethod
    def execution_mode(cls) -> ExecutionMode:
        pass

    @classmethod
    def get_registered_action_function(
            cls, data: dict[str, object], addition_params: dict[str, object] | None = None
    ) -> RegisteredFunctionExecutor[ActionNodeOutput]:
        try:
            a_params = addition_params if addition_params else {}
            a_params.update({"output": "", "state": _factory_sate_stub()})
            return get_registered_function(cls, ActionNodeOutput, data, a_params)
        except WorkflowConfigurationError as e:
            raise ActionConfigurationError(
                cls.ACTION_TYPE,
                "exception in get_registered_function"
            ) from e


class BaseAutomaticAction(BaseAction, ABC):
    def __init__(self, data: dict[str, object]):
        super().__init__(data)

    @abstractmethod
    def _execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        pass

    def execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        return self._execute(state, prev_output).update_parameters(prev_output)

    @classmethod
    def execution_mode(cls) -> ExecutionMode:
        return ExecutionMode.AUTOMATIC


class BaseInteractiveAction(BaseAction, ABC):
    def __init__(self, data: dict[str, object]):
        super().__init__(data)

    @abstractmethod
    def present(self, state: StateModel) -> PresentResponse:
        pass

    @classmethod
    def execution_mode(cls) -> ExecutionMode:
        return ExecutionMode.INTERACTIVE


class ActionWithFunction(BaseAutomaticAction, ABC):
    registered_function: RegisteredFunctionExecutor[ActionNodeOutput]

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.registered_function = self.get_registered_action_function(data)

    def _execute(self, state: StateModel, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        return self.registered_function.execute(
            parameters_modified=state.set_parameters_with_updater({"output": prev_output, "state": state})
        )
