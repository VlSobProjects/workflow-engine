"""ADR 012: build-time validation of the workflow ``inputs`` declaration block."""

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.codecs.base_codecs import PathCodec
from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.models.workflow import InputDeclaration, WorkflowModel


@pytest.fixture(autouse=True, scope="module")
def _codecs_registered(tmp_path_factory):
    # Building an engine runs the component loader, which registers the core codecs the type
    # validation resolves against.
    create_engine(tmp_path_factory.mktemp("codec-registration"))


def _base_workflow() -> dict[str, object]:
    return {
        "schema_version": "1",
        "flow_id": "f",
        "start_node_id": "N",
        "nodes": [{"id": "N", "action_type": "stop", "action_parameters": {}}],
    }


def _inputs(raw: object) -> tuple[InputDeclaration, ...]:
    return WorkflowModel.from_dict({**_base_workflow(), "inputs": raw}).inputs


def test_absent_inputs_is_empty_tuple():
    assert WorkflowModel.from_dict(_base_workflow()).inputs == ()


def test_empty_list_is_empty_tuple():
    assert _inputs([]) == ()


def test_order_and_required_default():
    inputs = _inputs([{"name": "a"}, {"name": "b", "required": False}])
    assert [d.name for d in inputs] == ["a", "b"]
    assert inputs[0].required is True
    assert inputs[1].required is False


def test_type_resolves_to_full_codec_name():
    (declaration,) = _inputs([{"name": "scan_root", "type": "Path"}])
    assert declaration.type.endswith(".Path")


def test_full_type_name_is_accepted():
    (declaration,) = _inputs([{"name": "depth", "type": "builtins.int"}])
    assert declaration.type == "builtins.int"


@pytest.mark.parametrize("stored_name", ["pathlib.Path", "pathlib._local.Path"])
def test_full_path_name_of_any_python_version_is_accepted(stored_name):
    (declaration,) = _inputs([{"name": "scan_root", "type": stored_name}])
    assert declaration.type == PathCodec.type_name()


@pytest.mark.parametrize("name", ["1abc", "a-b", "a:b", "a=b", "", "  "])
def test_invalid_name_charset_is_rejected(name):
    with pytest.raises(WorkflowConfigurationError):
        _inputs([{"name": name}])


@pytest.mark.parametrize("name", ["_x", "Abc9", "a_b_2"])
def test_valid_name_charset_is_accepted(name):
    (declaration,) = _inputs([{"name": name}])
    assert declaration.name == name


def test_duplicate_name_is_rejected():
    with pytest.raises(WorkflowConfigurationError):
        _inputs([{"name": "a"}, {"name": "a"}])


def test_unknown_codec_type_is_rejected():
    with pytest.raises(WorkflowConfigurationError):
        _inputs([{"name": "a", "type": "NoSuchCodec"}])


def test_inputs_not_a_list_is_rejected():
    with pytest.raises(WorkflowConfigurationError):
        _inputs({"name": "a"})


def test_entry_not_a_dict_is_rejected():
    with pytest.raises(WorkflowConfigurationError):
        _inputs(["a"])


def test_non_bool_required_is_rejected():
    with pytest.raises(WorkflowConfigurationError):
        _inputs([{"name": "a", "required": "yes"}])
