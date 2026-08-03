import pytest

from workflow_engine.actions.base_actions import BaseAction
from workflow_engine.exceptions import FunctionRuntimeError
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import FUNCTION_NAME_KEY, get_registered_function, register_function


@register_function
def function_exceptions() ->ActionNodeOutput:
    raise ValueError("Test value error")
    return ActionNodeOutput("Test value error")





def test_execute():
    func = get_registered_function(BaseAction,ActionNodeOutput,{FUNCTION_NAME_KEY: "function_exceptions"})
    with pytest.raises(FunctionRuntimeError,match="Test value error"):
        func.execute()
