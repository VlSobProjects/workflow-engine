from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from workflow_engine.exceptions import StateLoadError, StateLoadParameterError, WorkflowParameterError
from workflow_engine.output import ActionNodeOutput
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
    def load_state(self) -> StateModel:
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
                current_node=source_node_id,
                parameter_name=name,
                message="Value can't be None"
            )

        if not codec.can_decode(value):
            raise StateLoadParameterError(
                current_node=source_node_id,
                parameter_name=name,
                message=f"Value type {type(value).__name__} does not match codec {codec.python_type().__name__}"
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

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> StateModel:
        params:dict[str, object] = {}
        try:
            params["timestamp"] = datetime.fromisoformat(parameter_from_dict(data, "timestamp", str))
            work_dir = Path(parameter_from_dict(data, "work_dir", str))
            if work_dir.is_dir():
                params["work_dir"] = work_dir.absolute()
            else:
                raise StateLoadError(parameter_name="work_dir",message=f"Invalid work_dir path: '{work_dir}'")
            params["schema_version"] = parameter_from_dict(data, "schema_version", str)

            params["flow_id"] = parameter_from_dict(data, "flow_id", str)
            params["current_node_id"] = parameter_from_dict(data, "current_node_id", str)
            params["error_code"] = parameter_from_dict_optional(data,"error_code", str)
            params["error_msg"] = parameter_from_dict_optional(data,"error_msg", str)
            params["attempt_counters"] = parameter_from_dict_default(data,"attempt_counters", dict,{})
            params["visit_counters"] = parameter_from_dict_default(data,"visit_counters", dict,{})
            params["outputs"] = parameter_from_dict_default(data,"outputs", dict,{})
            params["errors"] = parameter_from_dict_default(data,"errors", dict,{})
            params["params"] = {
                k: ActionParameter.from_dict(v)
                for k, v in parameter_from_dict_default(data,"params", dict,{}).items()
            }
            guard_results = parameter_from_dict_default(data,"guard_results", dict,{})
            params["guard_results"] = {
                k: GuardRecord.from_list(parameter_from_dict(guard_results,str(k),list))
                for k in guard_results
            }
            params["artifacts"] = parameter_from_dict_default(data,"artifacts", dict,{})
            params["flow_budget"] = parameter_from_dict_default(data,"flow_budget", int,0)
            params["nodes_visited"] = parameter_from_dict_default(data,"nodes_visited", int,0)
        except (ValueError,WorkflowParameterError) as e:
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
                self.errors[curr_node_id] = f"[{datetime.now(tz=UTC)}]({output.error_code}) {output.error_message}"
                self.error_code = output.error_code
                self.error_msg = output.error_message
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

    def add_parameter(self, param_name: str, param_value: object):
        self.params[param_name] = ActionParameter.create(self.current_node_id, param_name, param_value)
