import pytest

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.registry.action_registry import ACTION_REGISTRY
from workflow_engine.registry.function_registry import (
    FUNCTION_REGISTRY,
    VALIDATOR_REGISTRY,
)
from workflow_engine.registry.type_registry import CODEC_REGISTRY

COMPONENT_REPORT = False


@pytest.fixture
def load_engine(tmp_path):
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=str(tmp_path)))
    engine = bootstrap.build_engine()
    global COMPONENT_REPORT
    if not COMPONENT_REPORT:
        print("\n" + engine.components_report())
        COMPONENT_REPORT = True
    return engine


def test_action_registration(load_engine):
    assert len(VALIDATOR_REGISTRY) > 0
    assert len(FUNCTION_REGISTRY) > 0
    assert len(ACTION_REGISTRY) > 0
    assert len(CODEC_REGISTRY) > 0
    print(f"\nRegistered Validators: {list(VALIDATOR_REGISTRY.keys())}")
    print(f"Registered Functions: {list(FUNCTION_REGISTRY.keys())}")
    print(f"Registered Codecs: {list(CODEC_REGISTRY.keys())}")
    for k, v in ACTION_REGISTRY.items():
        print(f"Registered Action: {k} -> {v.__name__}")
