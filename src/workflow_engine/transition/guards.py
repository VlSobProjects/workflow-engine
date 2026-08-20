"""Guards: the single predicate concept of the engine.

A guard answers yes or no about an action result. It never writes anything: the caller passes a
trace list and the guard appends a record of what it answered, so that an execution can be explained
afterwards. See ADR 002.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final

from workflow_engine.exceptions import WorkflowParameterConfigurationError, WorkflowParameterError
from workflow_engine.function_injection import run_guard_function
from workflow_engine.models.state import GuardRecord, StateReadOnlyView
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import (
    FUNCTION_NAME_KEY,
    RegisteredFunctionExecutor,
    get_registered_function,
)
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_default, render_value_as_text

REVERSED_KEY = "reversed"
ALL_OF_KEY = "all_of"
ANY_OF_KEY = "any_of"
ERRORS_KEY = "errors"
NO_ERROR_NAME = "no_error"


class BaseGuard(ABC):
    """A predicate over an action result and the state."""

    negated: bool = False

    def __init__(self, data: dict[str, object]):
        self.negated = parameter_from_dict_default(data, REVERSED_KEY, bool, False)

    @abstractmethod
    def _check(self, output: ActionNodeOutput, state: StateReadOnlyView, trace: list[GuardRecord] | None) -> bool:
        """Answer without applying negation and without recording."""

    @abstractmethod
    def _name(self) -> str:
        """Name the rule, ignoring negation."""

    def name(self) -> str:
        return f"not {self._name()}" if self.negated else self._name()

    def check(self, output: ActionNodeOutput, state: StateReadOnlyView, trace: list[GuardRecord] | None = None) -> bool:
        result = self._check(output, state, trace)
        if self.negated:
            result = not result
        if trace is not None:
            trace.append(GuardRecord(name=self.name(), passed=result))
        return result

    @classmethod
    def get_function(cls, data: dict[str, object]) -> RegisteredFunctionExecutor[bool]:
        """Return the registered function executor if this guard is a FunctionGuard, else None."""
        return get_registered_function(cls, bool, data, {"output": "", "action_output": ActionNodeOutput("")})

    @classmethod
    @abstractmethod
    def data_keys(cls) -> list[str]:
        """Configuration keys that identify this guard."""

    @classmethod
    def is_class(cls, data: dict[str, object]) -> bool:
        return all(key in data for key in cls.data_keys())


class ValueGuard(BaseGuard, ABC):
    """A guard comparing the output text with a configured value."""

    value: str

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.value = parameter_from_dict(data, self.data_keys()[0], str)

    def _name(self) -> str:
        return f"{self.data_keys()[0]}:{self.value}"

    def converted_value(self, state: StateReadOnlyView) -> str:
        """Resolve the configured value and render it as the text this guard compares.

        A resolved value is typed, so the rendering follows the one rule for text (ADR 008): a path
        compares in POSIX form, which is the form the functions that produce paths write.
        """
        return render_value_as_text(state.set_parameters({"value": self.value})["value"])

    @abstractmethod
    def _compare(self, output_text: str, value: str) -> bool:
        """Compare the output text with the resolved value."""

    def _check(self, output: ActionNodeOutput, state: StateReadOnlyView, trace: list[GuardRecord] | None) -> bool:
        return self._compare(output.output_text, self.converted_value(state))


class ContainsGuard(ValueGuard):
    """Output contains only the configured value."""

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["contains"]

    def _compare(self, output_text: str, value: str) -> bool:
        return value in output_text


class EqualsGuard(ValueGuard):
    """Output equal to the configured value."""

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["equals"]

    def _compare(self, output_text: str, value: str) -> bool:
        return value == output_text


class StartsWithGuard(ValueGuard):
    """Output starts with the configured value."""

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["starts_with"]

    def _compare(self, output_text: str, value: str) -> bool:
        return output_text.startswith(value)


class EndsWithGuard(ValueGuard):
    """Output ends with the configured value."""

    @classmethod
    def data_keys(cls) -> list[str]:
        return ["ends_with"]

    def _compare(self, output_text: str, value: str) -> bool:
        return output_text.endswith(value)


class FunctionGuard(BaseGuard):
    """A guard backed by a registered function that returns a boolean."""

    registered_validator: RegisteredFunctionExecutor[bool]
    function_name: str

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        self.function_name = parameter_from_dict(data, FUNCTION_NAME_KEY, str)
        self.registered_validator = self.get_function(data)

    @classmethod
    def data_keys(cls) -> list[str]:
        return [FUNCTION_NAME_KEY]

    def _name(self) -> str:
        return self.function_name

    def _check(self, output: ActionNodeOutput, state: StateReadOnlyView, trace: list[GuardRecord] | None) -> bool:
        # The state is deliberately not handed to the function. A guard reads the state only through
        # the parameter references the engine resolves for it, so it cannot write to it. See ADR 002.
        return run_guard_function(self.registered_validator, state, output)


class ErrorCodeGuard(BaseGuard):
    """A guard that holds when the action failed with one of the configured error codes."""

    error_codes: list[str]

    def __init__(self, data: dict[str, object]):
        super().__init__(data)
        error_codes = parameter_from_dict(data, ERRORS_KEY, list)
        for index, code in enumerate(error_codes):
            if not isinstance(code, str):
                raise WorkflowParameterError(
                    param_name=f"{ERRORS_KEY}[{index}]", param_type=type(code), expected_type=str
                )
        self.error_codes = error_codes

    @classmethod
    def data_keys(cls) -> list[str]:
        return [ERRORS_KEY]

    def _name(self) -> str:
        return f"{ERRORS_KEY}:{','.join(self.error_codes)}"

    def _check(self, output: ActionNodeOutput, state: StateReadOnlyView, trace: list[GuardRecord] | None) -> bool:
        return output.error_code is not None and output.error_code in self.error_codes


class NoErrorGuard(BaseGuard):
    """A guard that holds when the action produced no error code."""

    def __init__(self, data: dict[str, object] | None = None):
        super().__init__(data or {})

    @classmethod
    def data_keys(cls) -> list[str]:
        return [NO_ERROR_NAME]

    def _name(self) -> str:
        return NO_ERROR_NAME

    def _check(self, output: ActionNodeOutput, state: StateReadOnlyView, trace: list[GuardRecord] | None) -> bool:
        return output.error_code is None


class GroupGuard(BaseGuard, ABC):
    """A guard over a list of guards. Children are recorded before the group itself."""

    guards: list[BaseGuard]

    def __init__(self, data: dict[str, object] | None = None, guards: list[BaseGuard] | None = None):
        super().__init__(data or {})
        if guards is not None:
            self.guards = guards
            return
        if data is None:
            raise WorkflowParameterError(
                param_name="data",
                param_type=type(None),
                expected_type=dict,
                message=f"{type(self).__name__} needs either a configuration or a list of guards",
            )
        key = self.data_keys()[0]
        entries = parameter_from_dict(data, key, list)
        if len(entries) == 0:
            raise WorkflowParameterError(
                param_name=key,
                param_type=type(None),
                expected_type=list,
                message=f"'{key}' must not be empty, a group needs at least one guard",
            )
        built = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise WorkflowParameterError(param_name=f"{key}[{index}]", param_type=type(entry), expected_type=dict)
            built.append(guard_factory(entry))
        self.guards = built

    def _name(self) -> str:
        return self.data_keys()[0]


class AllOfGuard(GroupGuard):
    """All guards must pass for this guard to pass."""

    @classmethod
    def data_keys(cls) -> list[str]:
        return [ALL_OF_KEY]

    def _check(self, output: ActionNodeOutput, state: StateReadOnlyView, trace: list[GuardRecord] | None) -> bool:
        return all(guard.check(output, state, trace) for guard in self.guards)


class AnyOfGuard(GroupGuard):
    """At least one guard must pass for this guard to pass."""

    @classmethod
    def data_keys(cls) -> list[str]:
        return [ANY_OF_KEY]

    def _check(self, output: ActionNodeOutput, state: StateReadOnlyView, trace: list[GuardRecord] | None) -> bool:
        return any(guard.check(output, state, trace) for guard in self.guards)


GUARD_CLASSES: Final[tuple[type[BaseGuard], ...]] = (
    ContainsGuard,
    EqualsGuard,
    StartsWithGuard,
    EndsWithGuard,
    FunctionGuard,
    ErrorCodeGuard,
    NoErrorGuard,
    AllOfGuard,
    AnyOfGuard,
)


def guard_factory(data: dict[str, object]) -> BaseGuard:
    for guard_class in GUARD_CLASSES:
        if guard_class.is_class(data):
            return guard_class(data)
    raise WorkflowParameterConfigurationError(f"Failed to create a guard from: {data}")


def negated_guard(data: dict[str, object]) -> tuple[BaseGuard, str]:
    """Build the negation of a configured guard, and return it with the name of the original.

    Used to expand a post-condition: the transition is taken when the check does not hold, and the
    node then fails under the name of the check itself rather than under its negation.
    """
    guard = guard_factory(data)
    name = guard.name()
    guard.negated = not guard.negated
    return guard, name
