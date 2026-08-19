import datetime
from pathlib import Path
from typing import Annotated

import pytest

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.exceptions import FunctionRuntimeError
from workflow_engine.models.state import StateModel, StateReadOnlyView
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    FUNCTION_PARAMETERS_KEY,
    get_registered_function,
    register_function,
)


@register_function
def function_exceptions() -> ActionNodeOutput:
    raise ValueError("Test value error")
    return ActionNodeOutput("Test value error")


def test_execute():
    func = get_registered_function(BaseAction, ActionNodeOutput, {FUNCTION_NAME_KEY: "function_exceptions"})
    with pytest.raises(FunctionRuntimeError, match="Test value error"):
        func.execute()


@register_function
def function_exceptions_with_params(text: Annotated[str, "Text the function fails on"]) -> ActionNodeOutput:
    raise ValueError(f"Test value error on {text}")


@pytest.fixture
def injected_state() -> StateReadOnlyView:
    """The read-only view the engine injects into every call, as a real one and not a stand-in."""
    return StateReadOnlyView.from_state(
        StateModel(
            timestamp=datetime.datetime.now(tz=datetime.UTC),
            work_dir=Path(),
            schema_version="1",
            flow_id="test",
            session_id="test-session-id",
            current_node_id="test_node_id",
        )
    )


def test_execute_reports_the_declared_parameters_without_the_injected_ones(injected_state):
    """The engine injects `state` and `output` into every call; neither belongs in the failure text."""
    func = get_registered_function(
        BaseAction,
        ActionNodeOutput,
        {
            FUNCTION_NAME_KEY: "function_exceptions_with_params",
            FUNCTION_PARAMETERS_KEY: {"text": "payload"},
        },
    )

    with pytest.raises(FunctionRuntimeError) as error:
        func.execute(parameters_modified=lambda d: {**d, "output": None, "state": injected_state})

    message = str(error.value)
    assert "'text': 'payload'" in message
    assert "state" not in message
    assert "StateReadOnlyView" not in message
    assert "Test value error on payload" in message


def test_execute_does_not_wrap_a_failure_the_function_already_reported():
    """A function that raised FunctionRuntimeError about itself is reported once, not twice."""
    func = get_registered_function(BaseAction, ActionNodeOutput, {FUNCTION_NAME_KEY: "function_reports_itself"})

    with pytest.raises(FunctionRuntimeError) as error:
        func.execute()

    message = str(error.value)
    assert message.count("function_reports_itself") == 1
    assert "Error executing registered function" not in message
    assert "No message" not in message


@register_function
def function_reports_itself() -> ActionNodeOutput:
    raise FunctionRuntimeError(function_name="function_reports_itself", message="the source file does not exist")
