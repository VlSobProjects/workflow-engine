"""ADR 012: parsing of the ``--input NAME[:TYPE]=VALUE`` assignment grammar."""

import pytest

from workflow_engine.exceptions import WorkflowInputError
from workflow_engine.inputs import parse_input_assignment


def test_name_value_without_type():
    assignment = parse_input_assignment("depth=3")
    assert (assignment.name, assignment.type, assignment.value) == ("depth", None, "3")


def test_name_type_value():
    assignment = parse_input_assignment("scan_root:Path=/data")
    assert (assignment.name, assignment.type, assignment.value) == ("scan_root", "Path", "/data")


def test_missing_equals_is_error():
    with pytest.raises(WorkflowInputError):
        parse_input_assignment("scan_root:Path")


def test_value_may_contain_equals_and_colon():
    assignment = parse_input_assignment("q=a=b:c=d")
    assert assignment.name == "q"
    assert assignment.type is None
    assert assignment.value == "a=b:c=d"


def test_typed_value_may_contain_equals_colon_and_spaces():
    assignment = parse_input_assignment("root:Path=C:/data to scan=x")
    assert (assignment.name, assignment.type) == ("root", "Path")
    assert assignment.value == "C:/data to scan=x"


def test_value_may_contain_json():
    assignment = parse_input_assignment('columns:list=["Path", "Size"]')
    assert assignment.type == "list"
    assert assignment.value == '["Path", "Size"]'


def test_first_colon_before_first_equals_splits_the_type():
    # The type separator is the first ':' in the left part; a ':' in the value is untouched.
    assignment = parse_input_assignment("t:builtins.int=10:20")
    assert (assignment.name, assignment.type, assignment.value) == ("t", "builtins.int", "10:20")


def test_value_starting_with_dash_is_a_single_argument():
    assignment = parse_input_assignment("flag=-x")
    assert assignment.value == "-x"


def test_empty_name_is_parsed_and_left_to_the_binder():
    # Parsing does not validate the name; an empty/undeclared name is rejected at bind time.
    assignment = parse_input_assignment("=value")
    assert assignment.name == ""
    assert assignment.value == "value"
