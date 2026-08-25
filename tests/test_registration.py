import sys

import pytest

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.component_loader import ComponentLoader
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.registry.action_registry import (
    ACTION_DESCRIPTIONS,
    ACTION_NOTES,
    ACTION_OPERATOR_METADATA,
    ACTION_REGISTRY,
    get_registered_actions_info,
)
from workflow_engine.registry.function_registry import (
    FUNCTION_REGISTRY,
    VALIDATOR_REGISTRY,
)
from workflow_engine.registry.type_registry import CODEC_REGISTRY

COMPONENT_REPORT = False


@pytest.fixture
def load_engine(tmp_path):
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=tmp_path.as_posix()))
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


EXTERNAL_ACTION_MODULE = "wf_registration_external_action_probe"

EXTERNAL_ACTION_MODULE_SOURCE = """
from typing import ClassVar

from workflow_engine.actions.base_actions import BaseAutomaticAction
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.action_registry import register_action


@register_action("An action registered by a module outside the engine package.")
class ExternalProbeAction(BaseAutomaticAction):
    ACTION_TYPE: ClassVar[str] = "external_probe_action"

    def __init__(self, data: dict[str, object]) -> None:
        self.data = data

    def _execute(self, state: StateReadOnlyView, prev_output: ActionNodeOutput | None) -> ActionNodeOutput:
        return ActionNodeOutput(output_text="probe")
"""


@pytest.fixture
def external_action_module(tmp_path):
    """A module outside the engine package that registers one action, undone after the test.

    Registration is an import side effect, so the fixture restores the four action registries and
    drops the module from the import cache; otherwise the probe would leak into every later test.
    """
    (tmp_path / f"{EXTERNAL_ACTION_MODULE}.py").write_text(EXTERNAL_ACTION_MODULE_SOURCE, encoding="utf-8")
    sys.path.insert(0, tmp_path.as_posix())
    registries = (ACTION_REGISTRY, ACTION_DESCRIPTIONS, ACTION_NOTES, ACTION_OPERATOR_METADATA)
    originals = [(registry, dict(registry)) for registry in registries]
    try:
        yield EXTERNAL_ACTION_MODULE
    finally:
        sys.path.remove(tmp_path.as_posix())
        sys.modules.pop(EXTERNAL_ACTION_MODULE, None)
        for registry, original in originals:
            registry.clear()
            registry.update(original)


class TestExternalActionIsReportedAsExternal:
    """The loader tells core components from external ones by comparing two views of the registry.

    The comparison only holds when the first view is a copy: while the info call handed out
    `ACTION_DESCRIPTIONS` itself, that view grew with the plugins it was supposed to be measured
    against, the external section stayed empty and every action a plugin registered was reported as
    if the engine shipped it.
    """

    def test_an_action_of_an_external_module_is_not_reported_as_core(self, external_action_module):
        report = ComponentLoader(WorkflowEngineConfiguration(external_modules=(external_action_module,))).load_all()

        assert "external_probe_action" in report["External components"]["Actions"]
        assert "external_probe_action" not in report["Core components"]["Actions"]

    def test_a_core_action_stays_core_beside_it(self, external_action_module):
        report = ComponentLoader(WorkflowEngineConfiguration(external_modules=(external_action_module,))).load_all()

        assert "function" in report["Core components"]["Actions"]
        assert "function" not in report["External components"]["Actions"]


def test_the_registered_actions_info_is_a_snapshot_of_the_registry():
    """A caller holds a view of the registry, not the registry: writing into it registers nothing."""
    view = get_registered_actions_info()
    view["not_a_registered_action"] = "written into the view"

    assert "not_a_registered_action" not in get_registered_actions_info()
    assert "not_a_registered_action" not in ACTION_DESCRIPTIONS
