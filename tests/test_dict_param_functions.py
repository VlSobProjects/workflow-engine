"""The dictionary half of the collection function family, and the guard over an answered dictionary.

The G5 remainder of the 2026-08-23 audit: nothing created or set a dictionary parameter until the
`reorganize-folder` example named its assembly steps. `init_dict_param` prepares the parameter,
`set_dict_item` keys one value per pass, `append_to_dict_key` groups values under a key,
`filter_dict_by_value_size` extracts the groups that matter in code. `is_answer_keys_valid` is the
G4 guard: the keys of a dictionary a node bound as an answer, checked before the value reaches the
state.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.actions.modify_param_functions import (
    append_to_dict_key,
    filter_dict_by_value_size,
    init_dict_param,
    set_dict_item,
)
from workflow_engine.collection_param_handlers import PARAM_TYPE_MISMATCH, WriteParamMode
from workflow_engine.models.state import ActionParameter, StateModel, StateReadOnlyView
from workflow_engine.output import ActionNodeOutput
from workflow_engine.validators.output_function_validators import is_answer_keys_valid


@pytest.fixture(autouse=True, scope="module")
def _components_registered(tmp_path_factory):
    create_engine(tmp_path_factory.mktemp("registration"))


def _state(tmp_path: Path, **params: object) -> StateModel:
    return StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="test",
        current_node_id="DICT",
        session_id="test-session",
        params={
            name: ActionParameter.create(source_node_id="INIT", name=name, value=value)
            for name, value in params.items()
        },
    )


def _apply(state: StateModel, output: ActionNodeOutput) -> None:
    state.update(curr_node_id="DICT", save_as=None, output=output, next_node_id=None)


class TestInitDictParam:
    def test_it_creates_an_empty_dictionary(self, tmp_path):
        state = _state(tmp_path)

        output = init_dict_param("audit")
        _apply(state, output)

        assert output.error_code is None
        assert output.output_text == "audit"
        assert state.params["audit"].value == {}

    def test_an_existing_parameter_is_not_overwritten_by_default(self, tmp_path):
        state = _state(tmp_path, audit={"kept": "yes"})

        output = init_dict_param("audit")
        _apply(state, output)

        assert output.error_code == "param_overwrite_forbidden"
        assert state.params["audit"].value == {"kept": "yes"}

    def test_allow_overwrite_starts_a_fresh_assembly(self, tmp_path):
        state = _state(tmp_path, audit={"stale": "entry"})

        _apply(state, init_dict_param("audit", allow_overwrite=True))

        assert state.params["audit"].value == {}


class TestSetDictItem:
    def test_it_sets_one_key_of_the_dictionary(self, tmp_path):
        state = _state(tmp_path, categories={})

        output = set_dict_item("categories", "a.txt", "documents", StateReadOnlyView.from_state(state))
        _apply(state, output)

        assert output.error_code is None
        assert output.output_text == "a.txt"
        write = output.param_writes["categories"]
        assert write.mode == WriteParamMode.DICT_UPDATE
        assert state.params["categories"].value == {"a.txt": "documents"}

    def test_keys_accumulate_across_passes_and_a_reused_key_is_replaced(self, tmp_path):
        state = _state(tmp_path, categories={})

        for key, value in (("a.txt", "documents"), ("b.py", "code"), ("a.txt", "data")):
            _apply(state, set_dict_item("categories", key, value, StateReadOnlyView.from_state(state)))

        assert state.params["categories"].value == {"a.txt": "data", "b.py": "code"}

    def test_the_key_is_rendered_as_text_so_a_path_keys_in_posix_form(self, tmp_path):
        state = _state(tmp_path, categories={})

        output = set_dict_item("categories", Path("sub") / "a.txt", "documents", StateReadOnlyView.from_state(state))

        assert output.output_text == "sub/a.txt"
        assert output.param_writes["categories"].value == {"sub/a.txt": "documents"}

    def test_a_missing_parameter_is_the_configured_error_code(self, tmp_path):
        output = set_dict_item("absent", "key", "value", StateReadOnlyView.from_state(_state(tmp_path)))

        assert output.error_code == "param_not_found"
        assert output.param_writes == {}
        assert "init_dict_param" in (output.error_msg or "")

    def test_a_parameter_that_is_not_a_dictionary_is_a_type_mismatch(self, tmp_path):
        state = _state(tmp_path, categories=["a list"])

        output = set_dict_item("categories", "key", "value", StateReadOnlyView.from_state(state))

        assert output.error_code == PARAM_TYPE_MISMATCH
        assert output.param_writes == {}


class TestAppendToDictKey:
    def test_a_new_key_starts_its_group_with_the_value(self, tmp_path):
        state = _state(tmp_path, groups={})

        output = append_to_dict_key("groups", "hash-1", "a.txt", StateReadOnlyView.from_state(state))
        _apply(state, output)

        assert output.error_code is None
        assert output.output_text == "hash-1"
        assert state.params["groups"].value == {"hash-1": ["a.txt"]}

    def test_values_group_under_their_keys_across_passes(self, tmp_path):
        state = _state(tmp_path, groups={})

        for key, value in (("hash-1", "a.txt"), ("hash-2", "b.txt"), ("hash-1", "copy-of-a.txt")):
            _apply(state, append_to_dict_key("groups", key, value, StateReadOnlyView.from_state(state)))

        assert state.params["groups"].value == {"hash-1": ["a.txt", "copy-of-a.txt"], "hash-2": ["b.txt"]}

    def test_a_missing_parameter_is_the_configured_error_code(self, tmp_path):
        output = append_to_dict_key("absent", "key", "value", StateReadOnlyView.from_state(_state(tmp_path)))

        assert output.error_code == "param_not_found"
        assert "init_dict_param" in (output.error_msg or "")

    def test_a_parameter_that_is_not_a_dictionary_is_a_type_mismatch(self, tmp_path):
        state = _state(tmp_path, groups="a string")

        output = append_to_dict_key("groups", "key", "value", StateReadOnlyView.from_state(state))

        assert output.error_code == PARAM_TYPE_MISMATCH
        assert output.param_writes == {}

    def test_a_key_holding_something_that_is_not_a_list_is_a_type_mismatch(self, tmp_path):
        state = _state(tmp_path, groups={"hash-1": "not a list"})

        output = append_to_dict_key("groups", "hash-1", "a.txt", StateReadOnlyView.from_state(state))

        assert output.error_code == PARAM_TYPE_MISMATCH
        assert output.param_writes == {}


class TestFilterDictByValueSize:
    def test_it_keeps_the_groups_that_reach_the_minimum(self, tmp_path):
        state = _state(
            tmp_path, groups={"hash-1": ["a.txt", "b.txt"], "hash-2": ["c.txt"], "hash-3": ["d.txt", "e.txt"]}
        )

        output = filter_dict_by_value_size("groups", "duplicates", 2, StateReadOnlyView.from_state(state))
        _apply(state, output)

        assert output.error_code is None
        assert output.output_text == "2"
        assert state.params["duplicates"].value == {
            "hash-1": ["a.txt", "b.txt"],
            "hash-3": ["d.txt", "e.txt"],
        }
        assert state.params["groups"].value == {
            "hash-1": ["a.txt", "b.txt"],
            "hash-2": ["c.txt"],
            "hash-3": ["d.txt", "e.txt"],
        }

    def test_no_qualifying_group_writes_an_empty_dictionary_and_says_zero(self, tmp_path):
        state = _state(tmp_path, groups={"hash-1": ["only.txt"]})

        output = filter_dict_by_value_size("groups", "duplicates", 2, StateReadOnlyView.from_state(state))
        _apply(state, output)

        assert output.output_text == "0"
        assert state.params["duplicates"].value == {}

    def test_a_value_without_a_size_is_dropped(self, tmp_path):
        state = _state(tmp_path, groups={"hash-1": ["a.txt", "b.txt"], "count": 5})

        output = filter_dict_by_value_size("groups", "duplicates", 1, StateReadOnlyView.from_state(state))

        assert output.param_writes["duplicates"].value == {"hash-1": ["a.txt", "b.txt"]}

    def test_a_missing_parameter_is_the_configured_error_code(self, tmp_path):
        output = filter_dict_by_value_size("absent", "kept", 2, StateReadOnlyView.from_state(_state(tmp_path)))

        assert output.error_code == "param_not_found"

    def test_a_parameter_that_is_not_a_dictionary_is_a_type_mismatch(self, tmp_path):
        state = _state(tmp_path, groups=["a", "b"])

        output = filter_dict_by_value_size("groups", "kept", 2, StateReadOnlyView.from_state(state))

        assert output.error_code == PARAM_TYPE_MISMATCH


def _output_with(name: str, value: object) -> ActionNodeOutput:
    output = ActionNodeOutput(output_text="")
    output.set_param(name, value)
    return output


class TestIsAnswerKeysValid:
    def test_a_dictionary_within_the_allowed_keys_holds(self):
        output = _output_with("counts", {"code": 2, "documents": 1})

        assert is_answer_keys_valid(output, "counts", allowed=["code", "documents", "images"]) is True

    def test_a_key_outside_the_allowed_list_does_not_hold(self):
        output = _output_with("counts", {"code": 2, "invented": 1})

        assert is_answer_keys_valid(output, "counts", allowed=["code", "documents"]) is False

    def test_a_missing_required_key_does_not_hold(self):
        output = _output_with("counts", {"code": 2})

        assert is_answer_keys_valid(output, "counts", required=["code", "documents"]) is False

    def test_required_keys_all_present_hold_beside_extra_ones(self):
        output = _output_with("counts", {"code": 2, "documents": 1, "extra": 0})

        assert is_answer_keys_valid(output, "counts", required=["code", "documents"]) is True

    def test_without_lists_the_check_only_demands_a_dictionary(self):
        assert is_answer_keys_valid(_output_with("counts", {}), "counts") is True
        assert is_answer_keys_valid(_output_with("counts", "text"), "counts") is False

    def test_a_name_the_node_wrote_nothing_under_does_not_hold(self):
        assert is_answer_keys_valid(ActionNodeOutput(output_text=""), "counts", allowed=["code"]) is False

    def test_a_single_string_is_one_member_and_not_its_letters(self):
        output = _output_with("counts", {"c": 1})

        assert is_answer_keys_valid(output, "counts", allowed="code") is False
        assert is_answer_keys_valid(_output_with("counts", {"code": 1}), "counts", allowed="code") is True
