from abc import ABC, abstractmethod
from typing import get_origin

from workflow_engine.help_contract.models import HelpComponent, get_component_or_description, ComponentSource, \
    get_component_description
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput


class ComponentRander(ABC):
    component: HelpComponent

    def __init__(self, component: HelpComponent):
        self.component = component

    @abstractmethod
    def render(self) -> str:
        pass

def _add_description(description:str, lines: list[str], intend_num:int) -> None:
    d_list = description.strip().split("\n")
    intend = " " * intend_num
    for line in d_list:
        lines.append(f"{intend}{line.strip()}")

def _add_lines_with_intend(source_lines:list[str],target_list:list[str] ,intend_num:int) -> None:
    intend = " " * intend_num
    target_list.extend([f"{intend}{line.strip()}" for line in source_lines])

def _set_parameter(parameter:str, source: ComponentSource, p_description: str, p_type:type, lines: list[str], intend_num: int, step: int) -> None:
    intend = " " * intend_num
    com_or_desc = get_component_or_description(p_type, source)
    # lines.append(f"{step_intend}{parameter}: {p_description}")
    if isinstance(com_or_desc, str):
        _add_description(com_or_desc, lines, intend_num)
    elif isinstance(com_or_desc, HelpComponent):
        lines.append(f"{intend}{parameter}: {p_description}")
        lines.extend([f"{intend}Name: {com_or_desc.name}", f"{intend}Type: {com_or_desc.component_type}"])
        _add_description(com_or_desc.description, lines, intend_num)
        _render_parameters(source, com_or_desc.parameters, lines, intend_num+step, step)
        if com_or_desc.notes:
            _add_lines_with_intend(com_or_desc.notes, lines, intend_num + step)
    else:
        lines.append(f"{intend}{parameter}: {p_description}")

def _knowing_types_description(k_type:type)-> str | None:
    t_origin = get_origin(k_type) or k_type
    if t_origin is ActionNodeOutput:
        return "Action Output with output_text, error_code, error_msg and dictionary of WriteParam - channel to write parameters to the state"
    if t_origin is StateReadOnlyView:
        return "Read-only state view used to access parameters and artifacts"
    return None



def _render_parameters(source: ComponentSource, parameters: dict[str,tuple[type,str]] | None, lines: list[str], intend_num: int, step: int) -> None:
    if parameters:
        intend = " " * intend_num
        # step_intend = " " * (intend_num + step)
        lines.append(f"{intend}Parameters:")
        for parameter, value in parameters.items():
            p_type = value[0]
            p_description = value[1]
            knowing_param_d = _knowing_types_description(p_type)
            if knowing_param_d:
                _set_parameter(parameter, source, knowing_param_d, p_type, lines, intend_num+step, step)
            elif not unwarp_dict_type_to_lines(source, p_type, p_description, parameter, lines, intend_num+step, step):
                _set_parameter(parameter, source, p_description, p_type, lines, intend_num+step, step)

            # com_or_desc = get_component_or_description(p_type, source)
            # # lines.append(f"{step_intend}{parameter}: {p_description}")
            # if isinstance(com_or_desc, str):
            #     _add_description(com_or_desc, lines, intend_num+step)
            # elif isinstance(com_or_desc, HelpComponent):
            #     lines.append(f"{step_intend}{parameter}: {p_description}")
            #     lines.extend([f"{step_intend}Name: {com_or_desc.name}", f"{step_intend}Type: {com_or_desc.component_type}"])
            #     _add_description(com_or_desc.description, lines, intend_num + step)
            #     _render_parameters(source, com_or_desc.parameters, lines, intend_num + step, step)
            #     if com_or_desc.notes:
            #         _add_lines_with_intend(com_or_desc.notes, lines, intend_num + step)
            # else:
            #     lines.append(f"{step_intend}{parameter}: {p_description}")


def unwarp_dict_type_to_lines(source: ComponentSource,param_type:type, param_name:str, description:str, lines: list[str], intend_num: int, step: int)-> bool:
    if get_origin(param_type) is dict and hasattr(param_type, "__args__"):
        key_type, value_type = param_type.__args__
        _add_description(f"Dictionary: {description}", lines, intend_num)
        _set_parameter("Key",source,key_type.__name__, key_type,lines, intend_num+step, step)
        _set_parameter("Value",source,value_type.__name__, value_type,lines, intend_num+step, step)
        return True
    return False

class TextComponentRander(ComponentRander):


    def render(self) -> str:
        lines: list[str] = [
            f"Source: {self.component.source.value}",
            f"Type: {self.component.component_type.value}",
            "Type Description:"
        ]
        _add_description(get_component_description(self.component.component_type), lines, intend_num=3)
        lines.extend([f"Name: {self.component.name}","Description:"])
        _add_description(f"{self.component.description}", lines, intend_num=3)
        _render_parameters(self.component.source, self.component.parameters, lines, 0, 3)
        if self.component.notes:
            _add_lines_with_intend(self.component.notes, lines, 3)
        return "\n".join([l for l in lines if not l.isspace()]).strip()