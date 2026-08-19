from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum, auto
from pathlib import Path
from typing import Annotated, ClassVar

from workflow_engine.actions.action_present import AnswerContract, PresentResponse
from workflow_engine.exceptions import (
    ActionConfigurationError,
    ArtifactNotFoundError,
    ArtifactPathError,
    WorkflowConfigurationError,
)
from workflow_engine.models.state import StateModel, StateReadOnlyView
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
    get_registered_function,
)


class ExecutionMode(Enum):
    AUTOMATIC = auto()
    INTERACTIVE = auto()


# To pass in get_and_check_registered function as addition_params
# To check action function in configuration stage
# In case action function will have state:StateModel arg so will not accept None
def _factory_sate_stub() -> StateModel:
    return StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=Path("/"),
        schema_version="1",
        flow_id="default",
        current_node_id="start",
        session_id="none",
    )


class BaseAction(ABC):
    """Base of every action, built from the 'action_parameters' of a node.

    The base class keeps no configuration of its own: each subclass reads the keys it needs in its
    own constructor. Node level keys such as 'save_as' are not action parameters; the engine reads
    them from the node configuration.
    """

    ACTION_TYPE: ClassVar[str]

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
            raise ActionConfigurationError(cls.ACTION_TYPE, "exception in get_registered_function") from e

    @classmethod
    def get_action_docstring(cls) -> str:
        for action_class in inspect.getmro(cls):
            if doc := inspect.getdoc(action_class):
                return doc
        return ""


class BaseAutomaticAction(BaseAction):
    @abstractmethod
    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        """
        Args:
            state: The current read-only state of the workflow.
            prev_output: The output from the previous action node, if any.

        Returns:
            The returned ``ActionNodeOutput`` contains:
            - ``output_text``: The textual output.
            - ``error_code``: The error code, if execution failed.
            - ``error_msg``: The error message, if execution failed.
            - ``param_writes``: Parameter values to write to the workflow state.
            - ``artifacts``: Artifacts produced by the action.
        """
        raise NotImplementedError("Subclasses must implement the _execute method.")

    def execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        try:
            return self._execute(state, prev_output)
        except (ArtifactPathError, ArtifactNotFoundError) as e:
            return ActionNodeOutput(output_text="", error_code=e.error_code, error_msg=str(e))

    @classmethod
    def get_action_docstring(cls) -> str:
        doc = super().get_action_docstring()

        if execute_doc := cls._get_execute_doc():
            if doc:
                return f"{doc}\n\n{execute_doc}"
            return execute_doc

        return doc

    @classmethod
    def _get_execute_doc(cls) -> str:
        for action_class in inspect.getmro(cls):
            method = action_class.__dict__.get("_execute")

            if method is not None:
                return inspect.getdoc(method) or ""

        return ""

    @classmethod
    def execution_mode(cls) -> ExecutionMode:
        return ExecutionMode.AUTOMATIC


class BaseInteractiveAction(BaseAction):
    @abstractmethod
    def present(self, state: StateReadOnlyView) -> PresentResponse:
        raise NotImplementedError("Subclasses must implement the present method.")

    def answer_contract(self) -> AnswerContract:
        """What an answer to this node must carry. See ADR 013 §2.

        The engine validates an incoming answer against this contract, so it never needs to know which
        interactive action asked. An action that declares nothing accepts an answer that binds nothing.
        """
        return AnswerContract()

    @classmethod
    def execution_mode(cls) -> ExecutionMode:
        return ExecutionMode.INTERACTIVE

    @classmethod
    def get_execution_docstring(cls) -> str:
        method = getattr(cls, "_execute", None)
        doc = inspect.getdoc(method) if method else ""
        return doc if doc is not None else ""


class ActionWithFunction(BaseAutomaticAction):
    registered_function: Annotated[RegisteredFunctionExecutor[ActionNodeOutput], f"{FUNCTION_NAME_KEY}"]

    def __init__(self, data: dict[str, object]):
        self.registered_function = self.get_registered_action_function(data)

    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        """Execute the registered function with the current state and previous output."""
        return self.registered_function.execute(
            parameters_modified=state.set_parameters_with_updater({"output": prev_output, "state": state})
        )
