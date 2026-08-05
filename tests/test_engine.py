import pytest

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.exceptions import WorkflowEngineError
from workflow_engine.renderers.simple_render import SimplePresentResponseRender

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


def test_simple_workflow(load_engine, examples_dir):
    engine = load_engine
    session_id = engine.init_new_session(workflow_path=examples_dir / "simple_workflow.json")
    resp, state = engine.start_workflow(session_id=session_id)
    print(SimplePresentResponseRender(resp).render())
    assert state
    assert state.visit_counters["NODE_3"] == 1
    assert state.visit_counters["NODE_1"] == 1

    with pytest.raises(WorkflowEngineError):
        engine.init_new_session(workflow_path=examples_dir / "simple_workflow.json")

    with pytest.raises(WorkflowEngineError):
        engine.start_workflow(session_id="122334")
