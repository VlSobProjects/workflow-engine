import importlib
from pathlib import Path

import pytest

from workflow_engine.engine import sart_engine
from workflow_engine.registry.action_registry import ACTION_REGISTRY
from workflow_engine.registry.function_registry import (
    FUNCTION_REGISTRY,
    VALIDATOR_REGISTRY,
)
from workflow_engine.renderers.simple_render import SimplePresentResponseRender
from workflow_engine.storage.json_storage import JsonStorage


@pytest.fixture
def load_modules():
    importlib.import_module("workflow_engine.codecs.base_codecs")
    importlib.import_module("workflow_engine.validators.output_function_validators")
    importlib.import_module("workflow_engine.actions.base_functions")
    importlib.import_module("workflow_engine.actions.action_nodes")


@pytest.fixture
def registration(load_modules):
    assert len(VALIDATOR_REGISTRY) > 0
    assert len(FUNCTION_REGISTRY) > 0
    assert len(ACTION_REGISTRY) > 0
    print(f"Registered Validators: {list(VALIDATOR_REGISTRY.keys())}")
    print(f"Registered Functions: {list(FUNCTION_REGISTRY.keys())}")
    for k,v in ACTION_REGISTRY.items():
        print(f"Registered Action: {k} -> {v.__name__}")

@pytest.fixture
def init_storage_simple_workflow(registration, tmp_path):
    storage = JsonStorage(tmp_path)
    storage.start_workflow(Path("../examples/simple_workflow.json"))
    return storage



def test_sart_engine(init_storage_simple_workflow):
    resp = sart_engine(init_storage_simple_workflow, None)
    assert resp
    state = init_storage_simple_workflow.load_state()
    print(SimplePresentResponseRender(resp).render())
    assert state
    assert state.visit_counters["NODE_3"] == 1
    assert state.visit_counters["NODE_1"] == 1
