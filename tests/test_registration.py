import importlib

import pytest

from workflow_engine.registry.action_registry import ACTION_REGISTRY
from workflow_engine.registry.function_registry import (
    FUNCTION_REGISTRY,
    VALIDATOR_REGISTRY,
)


@pytest.fixture
def load_modules():
    importlib.import_module("workflow_engine.validators.output_function_validators")
    importlib.import_module("workflow_engine.actions.base_functions")
    importlib.import_module("workflow_engine.actions.action_nodes")


def test_action_registration(load_modules):
    assert len(VALIDATOR_REGISTRY) > 0
    assert len(FUNCTION_REGISTRY) > 0
    assert len(ACTION_REGISTRY) > 0
    print(f"Registered Validators: {list(VALIDATOR_REGISTRY.keys())}")
    print(f"Registered Functions: {list(FUNCTION_REGISTRY.keys())}")
    for k,v in ACTION_REGISTRY.items():
        print(f"Registered Action: {k} -> {v.__name__}")