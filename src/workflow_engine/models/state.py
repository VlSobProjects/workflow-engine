from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

from workflow_engine.exceptions import (
    StateLoadError,
    StateLoadParameterError,
    WorkflowEngineError,
    WorkflowParameterError,
)
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.type_registry import (
    Codec,
    convert_from_dict,
    find_codec,
)
from workflow_engine.tools import (
    check_param_type,
    parameter_from_dict,
    parameter_from_dict_default,
    parameter_from_dict_optional,
)


@dataclass(frozen=True)
class CollectionHandler[T]:
    collection_type: type[T]
    copy_fn: Callable[[T], T]
    append_fn: Callable[[T, object], None]

    def update(self, param: ActionParameter, update: object) -> ActionParameter:
        if isinstance(param.value, self.collection_type):
            copy_v = self.copy_fn(param.value)
            self.append_fn(copy_v, update)
            return ActionParameter.create(param.source_node_id, param.name, copy_v)
        else:
            raise WorkflowEngineError(
                f"Expected a {self.collection_type.__name__} for append/dict_update, "
                f"got {type(update).__name__} Check code, ActionParameter value type check "
                f"for append/dict_update mast be implemented"
            )


COLLECTION_HANDLERS: MappingProxyType[type[object], CollectionHandler[object]]

_COLLECTION_HANDLERS_MUT: dict[type[object], CollectionHandler[object]] = {}


def _update_dict(data: dict, updates: object) -> None:
    """Update a dictionary with another dictionary"""
    if isinstance(updates, dict):
        data.update(updates)
    else:
        raise WorkflowEngineError(
            f"Expected a dictionary for dict_update, "
            f"got {type(updates).__name__} Check code, ParamWrite value check for dict_update mast be implemented"
        )


def _register_collection[T](c_type: type[T], copy_fn: Callable[[T], T], append_fn: Callable[[T, object], None]) -> None:
    _COLLECTION_HANDLERS_MUT[c_type] = CollectionHandler[T](
        collection_type=c_type, copy_fn=copy_fn, append_fn=append_fn
    )


_register_collection(list, copy_fn=lambda x: list(x), append_fn=lambda x, v: x.append(v))
_register_collection(deque, copy_fn=lambda x: deque(x), append_fn=lambda x, v: x.append(v))
_register_collection(set, copy_fn=lambda x: set(x), append_fn=lambda x, v: x.add(v))
_register_collection(dict, copy_fn=lambda x: dict(x), append_fn=_update_dict)

COLLECTION_HANDLERS = MappingProxyType(_COLLECTION_HANDLERS_MUT)


@dataclass(frozen=True, slots=True)
class GuardRecord:
    """One answer of one guard, as recorded in the state. See ADR 002."""

    name: str
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "passed": self.passed}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> GuardRecord:
        name = parameter_from_dict(data, "name", str)
        passed = parameter_from_dict(data, "passed", bool)
        return cls(name=name, passed=passed)

    @classmethod
    def from_list(cls, data: list) -> list[GuardRecord]:
        return [cls.from_dict(check_param_type("item", dict, item)) for item in data]


class StateSource(ABC):
    @abstractmethod
    def load_state(self, session_id: str) -> StateModel:
        pass

    @abstractmethod
    def load_all_states(self) -> list[StateModel]:
        pass

    @abstractmethod
    def save_state(self, state: StateModel) -> None:
        pass


@dataclass
class ActionParameter:
    source_node_id: str
    name: str
    value: object
    codec: type[Codec]

    def __init__(self, source_node_id: str, name: str, value: object, codec: type[Codec]) -> None:
        if value is None:
            raise StateLoadParameterError(
                current_node=source_node_id, parameter_name=name, message="Value can't be None"
            )

        if not codec.can_decode(value):
            raise StateLoadParameterError(
                current_node=source_node_id,
                parameter_name=name,
                message=f"Value type {type(value).__name__} does not match codec {codec.python_type().__name__}",
            )
        self.source_node_id = source_node_id
        self.name = name
        self.value = value
        self.codec = codec

    @classmethod
    def create(cls, source_node_id: str, name: str, value: object) -> ActionParameter:
        return cls(source_node_id=source_node_id, name=name, value=value, codec=find_codec(value))

    def to_dict(self) -> dict[str, object]:
        return {
            "source_node_id": self.source_node_id,
            "name": self.name,
            "value": self.codec.convert_to_dict(self.value),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ActionParameter:
        source_node_id = parameter_from_dict(data, "source_node_id", str)
        name = parameter_from_dict(data, "name", str)
        value = parameter_from_dict(data, "value", object)
        value, codec = convert_from_dict(value)
        return cls(source_node_id=source_node_id, name=name, value=value, codec=codec)


@dataclass
class StateModel:
    """State model for a v2 questionnaire flow."""

    timestamp: datetime
    work_dir: Path
    schema_version: str
    flow_id: str
    current_node_id: str
    session_id: str
    error_code: str | None = field(default=None)
    error_msg: str | None = field(default=None)
    attempt_counters: dict[str, int] = field(default_factory=dict)  # validation retries
    visit_counters: dict[str, int] = field(default_factory=dict)  # loop safety
    outputs: dict[str, str] = field(default_factory=dict)  # normalized values
    errors: dict[str, str] = field(default_factory=dict)  # error messages
    params: dict[str, ActionParameter] = field(default_factory=dict)  # save_as results
    guard_results: dict[str, list[GuardRecord]] = field(default_factory=dict)  # latest attempt per node
    artifacts: dict[str, str] = field(default_factory=dict)  # folder in workdir with files
    flow_budget: int = field(default=0)  # engine-managed params: _flow_budget (int)
    nodes_visited: int = field(default=0)  # engine-managed params: _nodes_visited (int)

    def session_view(self) -> dict[str, object]:
        return {
            "work_dir": self.work_dir.as_posix(),
            "schema_version": self.schema_version,
            "flow_id": self.flow_id,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> StateModel:
        params: dict[str, object] = {}
        try:
            params["timestamp"] = datetime.fromisoformat(parameter_from_dict(data, "timestamp", str))
            work_dir = Path(parameter_from_dict(data, "work_dir", str))
            if work_dir.is_dir():
                params["work_dir"] = work_dir.absolute()
            else:
                raise StateLoadError(parameter_name="work_dir", message=f"Invalid work_dir path: '{work_dir}'")

            params["schema_version"] = parameter_from_dict(data, "schema_version", str)
            params["session_id"] = parameter_from_dict(data, "session_id", str)
            params["flow_id"] = parameter_from_dict(data, "flow_id", str)
            params["current_node_id"] = parameter_from_dict(data, "current_node_id", str)
            params["error_code"] = parameter_from_dict_optional(data, "error_code", str)
            params["error_msg"] = parameter_from_dict_optional(data, "error_msg", str)
            params["attempt_counters"] = parameter_from_dict_default(data, "attempt_counters", dict, {})
            params["visit_counters"] = parameter_from_dict_default(data, "visit_counters", dict, {})
            params["outputs"] = parameter_from_dict_default(data, "outputs", dict, {})
            params["errors"] = parameter_from_dict_default(data, "errors", dict, {})
            params["params"] = {
                k: ActionParameter.from_dict(v)
                for k, v in parameter_from_dict_default(data, "params", dict, {}).items()
            }
            guard_results = parameter_from_dict_default(data, "guard_results", dict, {})
            params["guard_results"] = {
                k: GuardRecord.from_list(parameter_from_dict(guard_results, str(k), list)) for k in guard_results
            }
            params["artifacts"] = parameter_from_dict_default(data, "artifacts", dict, {})
            params["flow_budget"] = parameter_from_dict_default(data, "flow_budget", int, 0)
            params["nodes_visited"] = parameter_from_dict_default(data, "nodes_visited", int, 0)
        except (ValueError, WorkflowParameterError) as e:
            raise StateLoadError(parameter_name="state", message=e.__repr__()) from e

        return cls(**params)

    def __post_init__(self):
        self.work_dir = self.work_dir.absolute()

    def set_parameters(
        self, parameters: dict[str, object], updater: dict[str, object] | None = None
    ) -> dict[str, object]:
        new_params = {}
        for param_name, param_value in parameters.items():
            if isinstance(param_value, str) and (param_value.startswith(("param.", "output."))):
                p_arr = param_value.split(".")
                p_source = p_arr[0]
                p_value = p_arr[1]
                if p_source == "param":
                    if p_value in self.params:
                        new_params[param_name] = self.params[p_value].value
                    else:
                        raise StateLoadParameterError(
                            self.current_node_id, p_value, f"Parameter not found in params: {self.params}"
                        )
                elif p_source == "output":
                    if p_value in self.outputs:
                        new_params[param_name] = self.outputs[p_value]
                    else:
                        raise StateLoadParameterError(
                            self.current_node_id, p_value, f"Parameter not found in output: {self.outputs}"
                        )
            else:
                new_params[param_name] = param_value

        new_params.update(updater or {})
        return new_params

    def set_parameters_with_updater(
        self, updater: dict[str, object]
    ) -> Callable[[dict[str, object]], dict[str, object]]:
        return lambda parameters: self.set_parameters(parameters, updater)

    def get_param[T](self, param_name: str, param_type: type[T] = object) -> T | None:
        if param_name in self.params:
            value = self.params[param_name].value
            if isinstance(value, param_type):
                return value
        return None

    def _update_cur_node(self, curr_node_id: str, output: ActionNodeOutput | None, save_as: str | None) -> None:
        if output:
            if output.output_text:
                self.outputs[curr_node_id] = output.output_text
            if output.error_code:
                self.errors[curr_node_id] = f"[{datetime.now(tz=UTC)}]({output.error_code}) {output.error_msg}"
                self.error_code = output.error_code
                self.error_msg = output.error_msg
            else:
                self.outputs[curr_node_id] = output.output_text
                if save_as:
                    self.params[save_as] = ActionParameter.create(
                        source_node_id=curr_node_id, name=save_as, value=output.output_text
                    )

    def _update_stats(self, next_node_id: str | None, curr_node_id: str) -> None:
        if next_node_id and next_node_id == curr_node_id:
            # update attempt_counters
            self.attempt_counters[curr_node_id] = self.attempt_counters.get(curr_node_id, 0) + 1
        else:
            # reset attempt_counters and update visit_counters
            self.visit_counters[curr_node_id] = self.visit_counters.get(curr_node_id, 0) + 1
            self.attempt_counters[curr_node_id] = 0
            self.nodes_visited += 1
            if next_node_id:
                self.current_node_id = next_node_id

    def info(self) -> list[str]:
        info = [
            f"last node id: {self.current_node_id}, total visits: {self.nodes_visited}, flow_budget: {self.flow_budget}"
        ]
        info += [
            f"Stat: Total errors: {len(self.errors)}, "
            f"Total outputs: {len(self.outputs)}, "
            f"Total params: {len(self.params)}"
        ]
        if self.error_code or self.error_msg:
            info.append(
                f"Last error: {self.error_code if self.error_code else 'N/A'}"
                f"{f'- {self.error_msg}' if self.error_msg else ''}"
            )
        info.append("Attempts:")
        info += [f"{k}: {v}" for k, v in self.attempt_counters.items()]
        info.append("Visits:")
        info += [f"{k}: {v}" for k, v in self.visit_counters.items()]
        return info

    def info_errors(self) -> list[str]:
        if len(self.errors) == 0:
            return []
        errors = ["All errors in current workflow:"]
        return errors + [f"{k}: {v}" for k, v in self.errors.items()]

    def info_params(self) -> list[str]:
        if len(self.params) == 0:
            return []
        params = ["All parameters in current workflow:"]
        return params + [f"{k}: {v}" for k, v in self.params.items()]

    def info_outputs(self) -> list[str]:
        if len(self.outputs) == 0:
            return []
        outputs = ["All outputs in current workflow:"]
        return outputs + [f"{k}: {v}" for k, v in self.outputs.items()]

    def info_guards(self) -> list[str]:
        if len(self.guard_results) == 0:
            return []
        guards = ["Guard results of the last attempt of each node:"]
        for node_id, records in self.guard_results.items():
            guards += [f"{node_id}: {record.name} -> {record.passed}" for record in records]
        return guards

    def record_guards(self, node_id: str, records: list[GuardRecord]) -> None:
        """Keep the guard answers of the latest attempt of a node."""
        self.guard_results[node_id] = records

    def update(self, curr_node_id: str, save_as: str | None, output: ActionNodeOutput | None, next_node_id: str | None):
        self._update_cur_node(curr_node_id, output, save_as)
        self._update_stats(next_node_id, curr_node_id)
        if output is not None and len(output.param_writes) > 0:
            for param_name, param_write in output.param_writes.items():
                error = self._process_param_write(param_name, param_write)
                if error is not None:
                    self.error_code, self.error_msg = error
                    output.error_code, output.error_msg = error
                    self.errors[curr_node_id] = f"[{self.error_code}] {self.error_msg}"
                    break

    def add_parameter(self, param_name: str, param_value: object):
        self.params[param_name] = ActionParameter.create(self.current_node_id, param_name, param_value)

    def _param_write_mode_check(self, param_name: str, param_write: ParamWrite) -> tuple[str, str] | None:
        match param_write.mode:
            case "replace", "dict_update", "append":
                if param_name not in self.params:
                    return (
                        f"param_not_found_for_{param_write.mode}",
                        f"Parameter {param_name} not found for {param_write.mode}",
                    )
            case "set":
                if not param_write.allow_overwrite and param_name in self.params:
                    return (
                        "param_overwrite_forbidden",
                        f"Parameter {param_name} exist in state params for ParamWrite "
                        f"and set allow_overwrite forbidden = True (default value)",
                    )
            case "append,dict_update":
                if type(self.params[param_name].value) not in COLLECTION_HANDLERS:
                    return (
                        "param_type_mismatch",
                        f"ActionParameter {param_name} type mismatch for append: "
                        f"expected({', '.join([t.__name__ for t in COLLECTION_HANDLERS])}) "
                        f"found: {self.params[param_name].codec.type_name()}",
                    )
            case "dict_update":
                if not isinstance(self.params[param_name].value, dict) or not isinstance(param_write.value, dict):
                    return "param_type_mismatch", (
                        f"ParamWrite {param_name} type mismatch for dict_update: "
                        f"expected (dict) found : {type(param_write.value).__name__}"
                    )

        return None

    def _process_param_write(self, param_name: str, param_write: ParamWrite) -> tuple[str, str] | None:
        error = self._param_write_mode_check(param_name, param_write)
        if error is not None:
            return error
        match param_write.mode:
            case "replace,set":
                self.params[param_name] = ActionParameter.create(self.current_node_id, param_name, param_write.value)
            case "append,dict_update":
                handler = COLLECTION_HANDLERS[type(self.params[param_name].value)]
                self.params[param_name] = handler.update(self.params[param_name], param_write.value)
            case _:
                raise WorkflowEngineError(
                    f"Unknown ParamWrite mode: {param_write.mode}. "
                    f"Check code, ParamWrite mode check mast be implemented"
                )
        return None
