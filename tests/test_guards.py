import copy
import datetime
from pathlib import Path

import pytest

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.engine import WorkflowEngine
from workflow_engine.exceptions import (
    FunctionConfigurationError,
    FunctionRuntimeError,
    WorkflowParameterConfigurationError,
    WorkflowParameterError,
)
from workflow_engine.models.state import ActionParameter, GuardRecord, StateModel, StateReadOnlyView
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    FUNCTION_PARAMETERS_KEY,
    register_validator,
)
from workflow_engine.transition.guards import (
    AllOfGuard,
    AnyOfGuard,
    BaseGuard,
    ContainsGuard,
    EndsWithGuard,
    EqualsGuard,
    ErrorCodeGuard,
    FunctionGuard,
    NoErrorGuard,
    StartsWithGuard,
    guard_factory,
    negated_guard,
)

CONTAINS_GUARD = {"contains": "test_string"}
CONTAINS_GUARD_2 = {"contains": "param.test_param"}
EQUALS_GUARD = {"equals": "test_string"}
EQUALS_GUARD_2 = {"equals": "param.test_param"}
STARTS_WITH_GUARD = {"starts_with": "test_string"}
STARTS_WITH_GUARD_2 = {"starts_with": "param.test_param"}
ENDS_WITH_GUARD = {"ends_with": "test_string"}
ENDS_WITH_GUARD_2 = {"ends_with": "param.test_param"}
FUNCTION_GUARD_1 = {FUNCTION_NAME_KEY: "is_output_exist_file"}
FUNCTION_GUARD_2 = {
    FUNCTION_NAME_KEY: "is_output_contains_str",
    FUNCTION_PARAMETERS_KEY: {"substring": "param.test_param"},
}
ERRORS_GUARD = {"errors": ["copy_failed", "file_not_found"]}
ANY_OF_GUARD = {"any_of": [CONTAINS_GUARD, {"starts_with": "new_test"}]}
ALL_OF_GUARD = {"all_of": [CONTAINS_GUARD, {"starts_with": "test"}]}
NESTED_GUARD = {
    "any_of": [
        EQUALS_GUARD,
        {"all_of": [CONTAINS_GUARD, {"starts_with": "new_test"}]},
        {"any_of": [ENDS_WITH_GUARD_2, {"starts_with": "param.test_param2"}]},
    ]
}
ERROR_FUNC_PARAMETERS_GUARD = {
    FUNCTION_NAME_KEY: "is_output_contains_str",
    FUNCTION_PARAMETERS_KEY: {"substring": ""},
}

GUARDS: dict[type[BaseGuard], list[dict[str, object]]] = {
    ContainsGuard: [CONTAINS_GUARD, CONTAINS_GUARD_2],
    EqualsGuard: [EQUALS_GUARD, EQUALS_GUARD_2],
    StartsWithGuard: [STARTS_WITH_GUARD, STARTS_WITH_GUARD_2],
    EndsWithGuard: [ENDS_WITH_GUARD, ENDS_WITH_GUARD_2],
    FunctionGuard: [FUNCTION_GUARD_1, FUNCTION_GUARD_2],
    ErrorCodeGuard: [ERRORS_GUARD],
    AnyOfGuard: [ANY_OF_GUARD],
    AllOfGuard: [ALL_OF_GUARD, NESTED_GUARD["any_of"][1]],
}


COMPONENT_REPORT = False


def create_engine(tmp_path: Path) -> WorkflowEngine:
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=tmp_path.as_posix()))
    engine = bootstrap.build_engine()
    global COMPONENT_REPORT
    if not COMPONENT_REPORT:
        print("\n" + engine.components_report())
        COMPONENT_REPORT = True
    return engine


@pytest.fixture
def load_engine(tmp_path):
    return create_engine(tmp_path)


@pytest.fixture
def state_base(load_engine):
    return StateModel(
        timestamp=datetime.datetime.now(tz=datetime.UTC),
        work_dir=Path(),
        schema_version="1",
        flow_id="test",
        session_id="test-session-id",
        params={
            "test_param": ActionParameter.create(name="test_param", value="string", source_node_id="test_node_id"),
            "test_param2": ActionParameter.create(
                name="test_param2", value="new_string2", source_node_id="test_node_id"
            ),
        },
        current_node_id="test_node_id",
    )


@pytest.fixture
def state_read_only(state_base):
    return StateReadOnlyView.from_state(state_base)


def out(text: str, error_code: str | None = None) -> ActionNodeOutput:
    return ActionNodeOutput(output_text=text, error_code=error_code)


def test_factory(load_engine):
    for guard_type, configs in GUARDS.items():
        for config in configs:
            assert isinstance(guard_factory(config), guard_type)


def test_unknown_guard(load_engine):
    with pytest.raises(WorkflowParameterConfigurationError, match="Failed to create a guard"):
        guard_factory({"unknown": "value"})


def test_contains_guard(state_read_only):
    assert guard_factory(CONTAINS_GUARD).check(out("this is a test_string"), state_read_only)
    assert guard_factory(CONTAINS_GUARD_2).check(out("string"), state_read_only)


def test_equals_guard(state_read_only):
    assert guard_factory(EQUALS_GUARD).check(out("test_string"), state_read_only)
    assert guard_factory(EQUALS_GUARD_2).check(out("string"), state_read_only)


def test_starts_with_guard(state_read_only):
    assert guard_factory(STARTS_WITH_GUARD).check(out("test_string in test"), state_read_only)
    assert guard_factory(STARTS_WITH_GUARD_2).check(out("string in test"), state_read_only)


def test_ends_with_guard(state_read_only):
    assert guard_factory(ENDS_WITH_GUARD).check(out("this is a test_string"), state_read_only)
    assert guard_factory(ENDS_WITH_GUARD_2).check(out("this is a string"), state_read_only)


def test_function_guard(state_read_only, tests_dir):
    guard = guard_factory(FUNCTION_GUARD_1)
    assert guard.check(out((tests_dir / "test_guards.py").as_posix()), state_read_only)
    assert not guard.check(out((tests_dir / "does_not_exist.py").as_posix()), state_read_only)
    assert guard_factory(FUNCTION_GUARD_2).check(out("this is a string"), state_read_only)


def test_error_code_guard(state_read_only):
    guard = guard_factory(ERRORS_GUARD)
    assert guard.check(out("", error_code="copy_failed"), state_read_only)
    assert not guard.check(out("", error_code="other"), state_read_only)
    assert not guard.check(out("ok"), state_read_only)


def test_no_error_guard(state_read_only):
    assert NoErrorGuard().check(out("ok"), state_read_only)
    assert not NoErrorGuard().check(out("", error_code="copy_failed"), state_read_only)


def test_negation(state_read_only):
    guard = guard_factory({**CONTAINS_GUARD, "reversed": True})
    assert guard.check(out("nothing here"), state_read_only)
    assert not guard.check(out("this is a test_string"), state_read_only)
    assert guard.name() == "not contains:test_string"


def test_negated_guard_keeps_the_original_name(state_read_only):
    guard, name = negated_guard(FUNCTION_GUARD_1)
    assert name == "is_output_exist_file"
    assert guard.name() == "not is_output_exist_file"
    assert guard.check(out("no such file"), state_read_only)


def test_negated_guard_on_an_already_reversed_check(state_read_only, tests_dir):
    guard, name = negated_guard({**FUNCTION_GUARD_1, "reversed": True})
    assert name == "not is_output_exist_file"
    assert guard.name() == "is_output_exist_file"
    # The post-condition "the output must not be a file" fails when the output is one.
    assert guard.check(out((tests_dir / "test_guards.py").as_posix()), state_read_only)
    assert not guard.check(out("no such file"), state_read_only)


def test_reversed_must_be_a_boolean(load_engine):
    with pytest.raises(WorkflowParameterError, match="of type: 'str' expected type: 'bool'"):
        guard_factory({**CONTAINS_GUARD, "reversed": "yes"})


def test_groups(state_read_only):
    assert guard_factory(ANY_OF_GUARD).check(out("new_test is a string"), state_read_only)
    assert not guard_factory(ANY_OF_GUARD).check(out("nothing"), state_read_only)
    assert guard_factory(ALL_OF_GUARD).check(out("test_string here"), state_read_only)
    assert not guard_factory(ALL_OF_GUARD).check(out("a test_string here"), state_read_only)


def test_nested_groups(state_read_only):
    guard = guard_factory(NESTED_GUARD)
    assert guard.check(out("new_string2 is a new test"), state_read_only)
    assert not guard.check(out("new_string is a new test"), state_read_only)


def test_a_group_rejects_an_empty_list(load_engine):
    with pytest.raises(WorkflowParameterError, match="must not be empty"):
        guard_factory({"all_of": []})


def test_a_group_rejects_a_value_that_is_not_a_list(load_engine):
    with pytest.raises(WorkflowParameterError, match="'all_of' of type: 'dict' expected type: 'list'"):
        guard_factory({"all_of": {"contains": "x"}})


def test_a_group_names_the_entry_that_is_not_a_guard(load_engine):
    with pytest.raises(WorkflowParameterError, match=r"'all_of\[1\]' of type: 'str' expected type: 'dict'"):
        guard_factory({"all_of": [CONTAINS_GUARD, "oops"]})


def test_error_codes_must_be_a_list_of_strings(load_engine):
    with pytest.raises(WorkflowParameterError, match="'errors' of type: 'str' expected type: 'list'"):
        guard_factory({"errors": "copy_failed"})
    with pytest.raises(WorkflowParameterError, match=r"'errors\[1\]' of type: 'int' expected type: 'str'"):
        guard_factory({"errors": ["copy_failed", 7]})


def test_trace_records_children_before_the_group(state_read_only):
    trace: list[GuardRecord] = []
    assert guard_factory(ALL_OF_GUARD).check(out("test_string here"), state_read_only, trace)
    assert [record.name for record in trace] == ["contains:test_string", "starts_with:test", "all_of"]
    assert all(record.passed for record in trace)


def test_trace_records_only_what_was_evaluated(state_read_only):
    trace: list[GuardRecord] = []
    assert not guard_factory(ALL_OF_GUARD).check(out("nothing"), state_read_only, trace)
    assert [record.name for record in trace] == ["contains:test_string", "all_of"]
    assert [record.passed for record in trace] == [False, False]


def test_guard_does_not_write_to_the_state(state_base, tests_dir):
    state_read = StateReadOnlyView.from_state(state_base)
    before = copy.deepcopy(state_base.__dict__)
    guard_factory(NESTED_GUARD).check(out("new_string2 is a new test"), state_read, [])
    guard_factory(FUNCTION_GUARD_1).check(out((tests_dir / "test_guards.py").as_posix()), state_read, [])
    guard_factory(ERRORS_GUARD).check(out("", error_code="copy_failed"), state_read, [])
    assert state_base.__dict__ == before


def test_argument_error_is_raised(state_read_only):
    guard = guard_factory(ERROR_FUNC_PARAMETERS_GUARD)
    with pytest.raises(FunctionRuntimeError):
        guard.check(out("this is a string"), state_read_only)


@register_validator
def guard_sees_the_error_code(action_output: ActionNodeOutput) -> bool:
    return action_output.error_code == "copy_failed"


@register_validator
def guard_asking_for_the_state(state: object) -> bool:
    return state is not None


def test_a_guard_function_can_read_the_whole_action_result(state_read_only):
    guard = guard_factory({FUNCTION_NAME_KEY: "guard_sees_the_error_code"})
    assert guard.check(out("", error_code="copy_failed"), state_read_only)
    assert not guard.check(out("ok"), state_read_only)


def test_a_guard_function_cannot_ask_for_the_state(load_engine):
    # The state is not among the injected parameters, so a function asking for it cannot be built.
    # If the argument check ever learns about injected parameters, this boundary has to be decided
    # again rather than reappearing by accident. See ADR 002.
    with pytest.raises(FunctionConfigurationError):
        guard_factory({FUNCTION_NAME_KEY: "guard_asking_for_the_state"})


class TestPathValueRendering:
    """A path parameter is compared in POSIX form, which is the form a path-producing node writes."""

    @pytest.fixture
    def state_with_path(self, load_engine, tmp_path):
        state = StateModel(
            timestamp=datetime.datetime.now(tz=datetime.UTC),
            work_dir=Path(),
            schema_version="1",
            flow_id="test",
            session_id="test-session-id",
            params={
                "target": ActionParameter.create(
                    name="target", value=Path("C:/out/copy.txt"), source_node_id="test_node_id"
                )
            },
            current_node_id="test_node_id",
        )
        return StateReadOnlyView.from_state(state)

    def test_a_path_parameter_matches_the_posix_output_of_the_node_that_produced_it(self, state_with_path):
        # What `copy_file` writes as its output text is `Path.as_posix()`, on every OS.
        assert guard_factory({"equals": "param.target"}).check(out("C:/out/copy.txt"), state_with_path)

    def test_a_native_separator_literal_no_longer_matches(self, state_with_path):
        # The consequence of the rule: a definition that worked around the old rendering by writing
        # native separators stops matching, because nothing in the engine produces that form.
        assert not guard_factory({"equals": r"C:\out\copy.txt"}).check(out("C:/out/copy.txt"), state_with_path)

    def test_a_path_parameter_is_contained_in_a_posix_text(self, state_with_path):
        assert guard_factory({"contains": "param.target"}).check(out("copied to C:/out/copy.txt ok"), state_with_path)
