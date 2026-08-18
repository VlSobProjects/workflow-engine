from pathlib import Path
from types import UnionType, NoneType
from typing import Optional, get_origin

import pytest

from workflow_engine.actions.action_nodes import StopAction, StopOnError, FunctionsAction
from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.engine import WorkflowEngine
from workflow_engine.help_contract.adapters.actions import adapt_action
from workflow_engine.help_contract.adapters.functions import adapt_function
from workflow_engine.help_contract.adapters.guards import adapt_validation
from workflow_engine.help_contract.builder import get_all_help_component
from workflow_engine.help_contract.models import ComponentSource, HelpComponent, COMPONENT_BY_TYPE, ComponentType
from workflow_engine.help_contract.renderers import TextComponentRander
from workflow_engine.registry.action_registry import get_registered_action
from workflow_engine.registry.function_registry import get_function_registered, VALIDATOR_REGISTRY

COMPONENT_REPORT = True


def create_engine(tmp_path: Path) -> WorkflowEngine:
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=tmp_path.as_posix()))
    engine = bootstrap.build_engine()
    global COMPONENT_REPORT
    if not COMPONENT_REPORT:
        print("\n" + engine.components_report())
        COMPONENT_REPORT = True
    return engine

@pytest.fixture
def load_engine(tmp_path):
    return create_engine(tmp_path)

def get_component_type_from_type(field_type:type) -> ComponentType | None:
    if field_type in COMPONENT_BY_TYPE:
        return COMPONENT_BY_TYPE[field_type]
    if hasattr(field_type, "__args__"):
        for f_type in field_type.__args__:
            if f_type is NoneType:
                continue
            else:
                for a_type in f_type.mro():
                    if a_type in COMPONENT_BY_TYPE:
                        return COMPONENT_BY_TYPE[a_type]



    return None


def test_doc_action(load_engine):
    components = load_engine.components
    assert components is not None
    actions = components["Core components"]["Actions"]
    assert actions
    for action in actions:
        action_cls = get_registered_action(action)
        action_help = adapt_action(action_cls, source=ComponentSource.CORE)
        assert action_help is not None
        assert isinstance(action_help, HelpComponent)
        print(f"\nAction: {action} : {action_help.action_type.name} : {action_help.summary} =================================\n")
        print(f"Source: {action_help.source.value}")
        print(f"Description: {action_help.description}")
        if action_help.parameters:
            print("Parameters:")
            for parameter, (param_type, param_description) in action_help.parameters.items():
                c_type = get_component_type_from_type(param_type)
                if c_type is not None:
                    print(f" {c_type}:   {str(param_type)}: {param_description}")
                print(f"    {parameter} ({str(param_type)}): {param_description}")
        if action_help.notes:
            for note in action_help.notes:
                print(f"Note: \n{note}\n")

def test_doc_function(load_engine):
    components = load_engine.components
    assert components is not None
    functions = components["Core components"]["Functions"]
    assert functions
    for function in functions:
        function_cls = get_function_registered(function)
        function_help = adapt_function(function_cls, source=ComponentSource.CORE)
        assert function_help is not None
        assert isinstance(function_help, HelpComponent)
        print(f"\n=============================== Function: {function} : {function_help.summary} =================================\n")
        print(f"Source: {function_help.source.value}")
        print(f"Description: {function_help.description}")
        if function_help.parameters:
            print("Parameters:")
            for parameter, (param_type, param_description) in function_help.parameters.items():
                print(f"    {parameter} ({str(param_type)}): {param_description}")
        if function_help.notes:
            for note in function_help.notes:
                print(f"Note: \n{note}\n")

def render_help_component(component:HelpComponent):
    print(TextComponentRander(component).render())

def test_text_render(load_engine):
    all_components = get_all_help_component(ComponentSource.CORE)
    for component_type, components in all_components.items():
        print(f"\n========================== Component: {component_type} =================================\n")
        for component in components:
            print("=========================================================================================")
            print(TextComponentRander(component).render())

def test_action_component(load_engine):
    render_help_component(adapt_action(FunctionsAction, source=ComponentSource.CORE))

def test_guard_component(load_engine):
    validator = VALIDATOR_REGISTRY["is_output_exist_folder"]
    render_help_component(adapt_validation(validator, source=ComponentSource.CORE))
