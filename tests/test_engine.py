import importlib

import pytest

from workflow_engine.engine import WorkflowSession
from workflow_engine.registry.action_registry import ACTION_REGISTRY
from workflow_engine.registry.function_registry import (
    FUNCTION_REGISTRY,
    VALIDATOR_REGISTRY,
)
from workflow_engine.renderers.simple_render import SimplePresentResponseRender


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
    for k, v in ACTION_REGISTRY.items():
        print(f"Registered Action: {k} -> {v.__name__}")


@pytest.fixture
def init_session(registration, tmp_path, examples_dir):
    # session = WorkflowSession(tmp_path)
    # session.
    # storage.start_workflow(examples_dir / "simple_workflow.json")
    return WorkflowSession(tmp_path)


def test_simple_workflow(init_session, examples_dir):
    resp,session_id = init_session.create_new_session(examples_dir / "simple_workflow.json")
    assert resp
    storage = init_session.load_storage(session_id)
    state = storage.load_state()
    print(SimplePresentResponseRender(resp).render())
    assert state
    assert state.visit_counters["NODE_3"] == 1
    assert state.visit_counters["NODE_1"] == 1
