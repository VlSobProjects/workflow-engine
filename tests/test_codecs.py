import importlib
import json
from collections import deque
from pathlib import Path

import pytest

from workflow_engine.codecs.base_codecs import (
    DequeCodec,
    DictCodec,
    IntCodec,
    ListCodec,
    NumberCodec,
    PathCodec,
    SetCodec,
    StringCodec,
)
from workflow_engine.exceptions import StateLoadParameterError
from workflow_engine.models.state import ActionParameter
from workflow_engine.registry.type_registry import NoCodec


@pytest.fixture
def load_modules():
    importlib.import_module("workflow_engine.codecs.base_codecs")


def test_params():
    param = ActionParameter.create("source_node_id", "name", "value")
    assert isinstance(param.codec, type(StringCodec))
    param = ActionParameter.create("source_node_id", "name", 123)
    assert isinstance(param.codec, type(NumberCodec))
    param = ActionParameter.create("source_node_id", "name", Path("/test_registration.py"))
    assert isinstance(param.codec, type(PathCodec))
    param = ActionParameter.create("source_node_id", "name", {"test": "value"})
    assert isinstance(param.codec, type(DictCodec))
    param = ActionParameter.create("source_node_id", "name", ["test", "value"])
    assert isinstance(param.codec, type(ListCodec))
    param = ActionParameter.create("source_node_id", "name", deque(["test", "value"]))
    assert isinstance(param.codec, type(DequeCodec))
    param = ActionParameter.create("source_node_id", "name", {"test", "value"})
    assert isinstance(param.codec, type(SetCodec))


def test_collection_same_types():
    d = deque(
        [
            Path("/test_output_validators.py"),
            Path("/test_registration.py"),
            Path("/test_codecs.py"),
            Path("/test_engine.py"),
        ]
    )
    param = ActionParameter.create("source_node_id", "name", d)
    assert isinstance(param.codec, type(DequeCodec))
    data = param.to_dict()
    print(json.dumps(data, indent=4))
    param_converted = ActionParameter.from_dict(data)
    assert param.codec == param_converted.codec
    assert param.value == param_converted.value


def test_collection_different_types():
    d = deque(
        [
            Path("/test_output_validators.py"),
            "string_value",
            Path("/test_registration.py"),
            123,
            {"test": "value"},
            {"test1", "test2", "test3"},
        ]
    )
    param = ActionParameter.create("source_node_id", "name", d)
    assert isinstance(param.codec, type(DequeCodec))
    data = param.to_dict()
    param_converted = ActionParameter.from_dict(data)
    print(json.dumps(data, indent=4))
    assert param.codec == param_converted.codec
    assert param.value == param_converted.value


def test_exception_raised():
    with pytest.raises(StateLoadParameterError, match="Value can't be None"):
        ActionParameter.create("source_node_id", "name", None)
    with pytest.raises(StateLoadParameterError, match="Value can't be None"):
        ActionParameter("source_node_id", "name", None, NoCodec)
    with pytest.raises(StateLoadParameterError, match="does not match codec"):
        ActionParameter("source_node_id", "name", "string", IntCodec)


@pytest.mark.parametrize("stored_name", ["pathlib.Path", "pathlib._local.Path"])
def test_path_decodes_whichever_python_wrote_its_name(stored_name):
    data = {"source_node_id": "n", "name": "p", "value": {"object": "/a/b.txt", "object_type": stored_name}}
    param = ActionParameter.from_dict(data)
    assert param.codec is PathCodec
    assert param.value == Path("/a/b.txt")


@pytest.mark.parametrize("stored_name", ["pathlib.Path", "pathlib._local.Path"])
def test_path_item_decodes_whichever_python_wrote_its_name(stored_name):
    item = {"object": "/a/b.txt", "object_type": stored_name}
    data = {
        "source_node_id": "n",
        "name": "q",
        "value": {"object": [item], "object_type": DequeCodec.type_name()},
    }
    param = ActionParameter.from_dict(data)
    assert param.codec is DequeCodec
    assert param.value == deque([Path("/a/b.txt")])


def test_unknown_codec_name_is_left_undecoded():
    stored = {"object": "x", "object_type": "no_such_module.NoSuchType"}
    param = ActionParameter.from_dict({"source_node_id": "n", "name": "u", "value": stored})
    assert param.codec is NoCodec
    assert param.value == stored
