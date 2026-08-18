from abc import ABC
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType, NoneType
from typing import Final, ClassVar, get_origin

from workflow_engine.actions.base_actions import ExecutionMode, BaseAction
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import FUNCTION_NAME_KEY, FUNCTION_PARAMETERS_KEY, \
    RegisteredFunctionExecutor
from workflow_engine.registry.type_registry import Codec
from workflow_engine.transition.guards import BaseGuard


class ComponentSource(Enum):
    CORE = "core"
    EXTERNAL = "external"


class ComponentType(Enum):
    ACTION = "action"
    FUNCTION = "function"
    VALIDATION_FUNCTION = "validation function"
    GUARD = "guard"
    CODEC = "codec"




COMPONENT_BY_TYPE: Final[MappingProxyType[type,ComponentType]] = MappingProxyType({
    BaseAction: ComponentType.ACTION,
    Codec: ComponentType.CODEC,
    RegisteredFunctionExecutor[ActionNodeOutput]: ComponentType.FUNCTION,
    RegisteredFunctionExecutor[bool]: ComponentType.VALIDATION_FUNCTION,
})



COMPONENT_DESCRIPTION: Final[MappingProxyType[ComponentType, str]] = MappingProxyType({
    ComponentType.ACTION:
        """
        Action is class which represent node action performing during workflow execution.
        Action must be registered in action registry and can be used by workflow node.
        Can be 2 types: automatic and interactive. 
        Automatic action will be executed without user interaction an return output.
        Interactive action will require user input to proceed workflow execution to the next node by transition,
        Interactive action return instruction how to proceed workflow execution to the next node.
        Transition to the next can be strate, based on action or user output as result of guard function.
        """,
    ComponentType.FUNCTION:
    f"""
    {FUNCTION_NAME_KEY}: $function_name$ must be registered in function registry.
    {FUNCTION_PARAMETERS_KEY}: parameters of the function. 
    Automatically provided parameters:
        - 'state': StateReadOnlyView object which provide read-only access to the workflow state
        - 'output': ActionNodeOutput object which provide access to the previous action output
    Parameter value can be evaluated from the state parameters with prefix param.$param_name$ 
    or from the node output with prefix output.$node_id$.
    Function can save parameters to the state via parameters write channel.
    Function can return output_text, error code and error message which can be used in transitions to the next node or stop workflow execution.
    Function can rise exception which will stop workflow execution and return error code and error message.        
    """,
    ComponentType.VALIDATION_FUNCTION:
        """
        Guard function is used to validate transitions path to another node.
        Guard function must be registered in function registry and can be used by action node.
        Guard function can use StateReadOnlyView to read workflow state and action output ActionNodeOutput to perform its task.
        Guard function can have any number of parameters but return type must be bool.
        """,
    ComponentType.CODEC:
        """
        Codec is class which is used to encode/decode parameter in state 
        which can be used by actions and functions via StateReadOnlyView parameters.
        Codec registered by full python type name and use methods to convert value to dict and from dict.
        Codec covert value recursively and can be used to convert complex data structures to dict and from dict.
        Codec must be registered in codec registry.
        Codec must implement encode and decode methods.
        """,
    ComponentType.GUARD:
        """
        Node.
        Guard is class which is used to validate transitions path to another node.
        Guard must be registered in guard registry and can be used by action node.
        Guard can use StateReadOnlyView to read workflow state and action output ActionNodeOutput to perform its task.
        Guard can have any number of parameters but return type must be bool.
        """,
})

def get_component_description(component_type: ComponentType) -> str:
    return COMPONENT_DESCRIPTION.get(component_type, "")

@dataclass(frozen=True)
class HelpComponent(ABC):
    name: str
    source: ComponentSource
    summary: str
    description:str
    parameters: dict[str,tuple[type,str]] | None
    notes: list[str] | None
    component_type: ClassVar[ComponentType]

    def get_component_description(self) -> str:
        return COMPONENT_DESCRIPTION[self.component_type]

@dataclass(frozen=True)
class ActionComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.ACTION
    action_type: ExecutionMode



@dataclass(frozen=True)
class FunctionComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.FUNCTION

@dataclass(frozen=True)
class ValidationComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.VALIDATION_FUNCTION

@dataclass(frozen=True)
class GuardComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.GUARD

@dataclass(frozen=True)
class CodecComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.CODEC

@dataclass
class HelpComponents:
    components: dict[ComponentType, HelpComponent]

def _component_by_type(field_type:type) -> ComponentType | None:
    if field_type in COMPONENT_BY_TYPE:
        return COMPONENT_BY_TYPE[field_type]
    if isinstance(field_type, type):
        for type_ in COMPONENT_BY_TYPE:
            if issubclass(field_type, get_origin(type_) or type_):
                return COMPONENT_BY_TYPE[type_]
    if hasattr(field_type, "__args__"):
        for f_type in field_type.__args__:
            if f_type is NoneType:
                continue
            elif f_type in COMPONENT_BY_TYPE:
                return COMPONENT_BY_TYPE[f_type]
            else:
                for a_type in f_type.mro():
                    if a_type in COMPONENT_BY_TYPE:
                        return COMPONENT_BY_TYPE[a_type]
    return None



def get_component_or_description(component_type:type,source:ComponentSource) -> str | HelpComponent | None:
    from workflow_engine.help_contract.adapters.actions import adapt_action
    from workflow_engine.help_contract.adapters.codecs import adapt_codec
    from workflow_engine.help_contract.adapters.guards import adapt_guard
    c_type = _component_by_type(component_type)
    if c_type is not None:
        if isinstance(component_type, type) and issubclass(component_type, BaseAction):
            return adapt_action(component_type, source)
        elif isinstance(component_type, type) and issubclass(component_type, Codec):
            return adapt_codec(component_type, source)
        elif isinstance(component_type, type) and issubclass(component_type, BaseGuard):
            return adapt_guard(component_type, source)
        else:
            return COMPONENT_DESCRIPTION[c_type]
    return None