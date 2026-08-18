"""ADR 012: binding typed input values to a session through the engine."""

import json
from collections import deque
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.engine import WorkflowEngine
from workflow_engine.exceptions import WorkflowInputError
from workflow_engine.inputs import parse_input_assignment
from workflow_engine.models.state import SessionEventCode


def _make_session(tmp_path: Path, inputs: list[dict], nodes: list[dict] | None = None) -> tuple[WorkflowEngine, str]:
    engine = create_engine(tmp_path)
    workflow = {
        "schema_version": "1",
        "flow_id": "f",
        "start_node_id": "N",
        "nodes": nodes
        or [
            {
                "id": "N",
                "action_type": "function",
                "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "x"}},
                "transitions": [{"stop": True}],
            }
        ],
        "inputs": inputs,
    }
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow))
    return engine, engine.init_new_session(workflow_path=workflow_path)


def _bind(engine: WorkflowEngine, session_id: str, *raw: str):
    return engine.set_inputs(session_id, [parse_input_assignment(item) for item in raw])


def test_declared_name_binds_value(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "label"}])
    _bind(engine, session_id, "label=hello")
    assert engine.runtime.state.params["label"].value == "hello"


def test_undeclared_name_is_rejected(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "label"}])
    with pytest.raises(WorkflowInputError):
        _bind(engine, session_id, "other=hello")


def test_typed_int_decode(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "depth", "type": "int"}])
    _bind(engine, session_id, "depth=3")
    value = engine.runtime.state.params["depth"].value
    assert value == 3 and isinstance(value, int)


def test_typed_path_decode_from_unquoted_string(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "root", "type": "Path"}])
    _bind(engine, session_id, "root:Path=C:/data")
    value = engine.runtime.state.params["root"].value
    assert value == Path("C:/data") and isinstance(value, Path)


def test_typed_list_decode_from_json(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "cols", "type": "list"}])
    _bind(engine, session_id, 'cols:list=["Path", "Size"]')
    assert engine.runtime.state.params["cols"].value == ["Path", "Size"]


def test_numeric_path_requires_json_quoting(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "root", "type": "Path"}])
    with pytest.raises(WorkflowInputError):
        _bind(engine, session_id, "root:Path=42")  # 42 parses as JSON int -> PathCodec rejects it


def test_numeric_path_as_json_string_decodes(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "root", "type": "Path"}])
    _bind(engine, session_id, 'root:Path="42"')
    assert engine.runtime.state.params["root"].value == Path("42")


def test_bare_and_full_type_names_agree(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "d", "type": "builtins.int"}])
    _bind(engine, session_id, "d:int=7")  # explicit bare + declared full, same codec
    assert engine.runtime.state.params["d"].value == 7


def test_disagreeing_types_are_rejected(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "d", "type": "int"}])
    with pytest.raises(WorkflowInputError):
        _bind(engine, session_id, "d:Path=7")


def test_untyped_value_is_literal_string_without_json_parse(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "raw"}])
    _bind(engine, session_id, "raw=3")  # no type anywhere -> stays the string "3"
    value = engine.runtime.state.params["raw"].value
    assert value == "3" and isinstance(value, str)


def test_declared_only_type_is_applied(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "depth", "type": "int"}])
    _bind(engine, session_id, "depth=5")  # no explicit type; declared int applies
    assert engine.runtime.state.params["depth"].value == 5


def test_duplicate_in_one_invocation_is_rejected(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "a"}])
    with pytest.raises(WorkflowInputError):
        _bind(engine, session_id, "a=1", "a=2")


def test_rebind_across_calls_overwrites_and_journals_both(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "a"}])
    _bind(engine, session_id, "a=1")
    _bind(engine, session_id, "a=2")
    assert engine.runtime.state.params["a"].value == "2"
    events = [e for e in engine.runtime.state.session_events if e.code == SessionEventCode.INPUTS_SET]
    assert len(events) == 2


def test_event_records_names_and_codecs_not_values(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "root", "type": "Path"}])
    _bind(engine, session_id, "root:Path=C:/data")
    event = next(e for e in engine.runtime.state.session_events if e.code == SessionEventCode.INPUTS_SET)
    assert event.actor == "operator"
    assert event.details["names"] == ["root"]
    assert event.details["codecs"]["root"].endswith(".Path")
    assert "C:/data" not in json.dumps(event.details)


def test_binding_after_start_is_rejected(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "label", "required": False}])
    engine.start_workflow(session_id=session_id)
    with pytest.raises(WorkflowInputError):
        _bind(engine, session_id, "label=late")


def test_typed_values_survive_save_and_load(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "root", "type": "Path"}, {"name": "depth", "type": "int"}])
    _bind(engine, session_id, "root:Path=C:/data", "depth=2")

    reloaded = create_engine(tmp_path)
    reloaded.get_status(session_id=session_id)
    params = reloaded.runtime.state.params
    assert isinstance(params["root"].value, Path)
    assert params["root"].value == Path("C:/data")
    assert isinstance(params["depth"].value, int)
    assert params["depth"].value == 2


def test_deque_input_round_trips(tmp_path):
    engine, session_id = _make_session(tmp_path, [{"name": "q", "type": "deque"}])
    _bind(engine, session_id, 'q:deque=["a", "b"]')
    assert engine.runtime.state.params["q"].value == deque(["a", "b"])
