from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from workflow_engine.exceptions import RuntimeParameterError
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.type_registry import (
    Codec,
    NoCodec,
    convert_from_dict,
    find_codec,
)


class StateSource(ABC):
    @abstractmethod
    def load_state(self) -> StateModel:
        pass

    @abstractmethod
    def save_state(self, state: StateModel) -> None:
        pass


@dataclass
class ActionParameter:
    source_node_id:str
    name: str
    value: object
    codec:type[Codec]

    @classmethod
    def create(cls, source_node_id:str, name: str, value: object) -> ActionParameter:
        codec = find_codec(value)
        if codec is None:
            codec = NoCodec
        return cls(
            source_node_id=source_node_id,
            name=name,
            value=value,
            codec=codec
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_node_id": self.source_node_id,
            "name": self.name,
            "value": self.codec.convert_to_dict(self.value),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ActionParameter:
        if "source_node_id" in data and "name" in data and "value" in data:
            source_node_id = data["source_node_id"]
            name = data["name"]
            value = data["value"]
            value, codec = convert_from_dict(value)       
            if isinstance(source_node_id, str) and isinstance(name, str):
                return cls(
                    source_node_id=source_node_id,
                    name=name,
                    value=value,
                    codec=codec,
                )
            else:
                raise RuntimeParameterError(name.__repr__(), source_node_id.__repr__(), value.__repr__(), "Invalid parameter types")
        else:
            raise RuntimeParameterError(data.get("name", "N/A").__repr__(), data.get("source_node_id", "N/A").__repr__(), data.get("value", "N/A").__repr__(), "Missing required keys in parameter dictionary")

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
    visit_counters: dict[str, int] = field(default_factory=dict)    # loop safety
    outputs: dict[str, str] = field(default_factory=dict)           # normalized values
    errors: dict[str, str] = field(default_factory=dict)            # error messages
    params: dict[str, ActionParameter] = field(default_factory=dict)            # save_as results
    artifacts: dict[str, str] = field(default_factory=dict) #folder in workdir with files
    flow_budget: int = 0                               # engine-managed params: _flow_budget (int)
    nodes_visited: int = 0                             # engine-managed params: _nodes_visited (int)

    def __post_init__(self):
        self.work_dir = self.work_dir.absolute()

    def set_parameters(self, parameters: dict[str, object], updater:dict[str, object] | None=None)->dict[str, object]:
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
                        raise RuntimeParameterError(param_name, self.current_node_id, param_value, f"Parameter not found in params: {self.params}")
                elif p_source == "output":
                    if p_value in self.outputs:
                        new_params[param_name] = self.outputs[p_value]
                    else:
                        raise RuntimeParameterError(param_name, self.current_node_id, param_value, "Parameter not found in output")
            else:
                new_params[param_name] = param_value

        new_params.update(updater or {})
        return new_params

    def set_parameters_with_updater(self,updater:dict[str, object])->Callable[[dict[str, object]], dict[str, object]]:
        return lambda parameters: self.set_parameters(parameters, updater)

    def get_param[T](self, param_name:str, param_type: type[T] = object)->T | None:
        if param_name in self.params:
            value = self.params[param_name].value
            if isinstance(value, param_type):
                return value
        return None

    def _update_cur_node(self, curr_node_id:str, output: ActionNodeOutput | None,save_as:str | None) ->None:
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
                        source_node_id=curr_node_id,
                        name=save_as,
                        value=output.output_text
                    )
    
    def _update_stats(self,next_node_id:str | None,curr_node_id:str) -> None:
        if next_node_id and next_node_id == curr_node_id:
            # update attempt_counters
            self.attempt_counters[curr_node_id] = self.attempt_counters.get(curr_node_id, 0) + 1
        else:
            # reset attempt_counters and update visit_counters
            self.visit_counters[curr_node_id] = self.visit_counters.get(curr_node_id, 0) + 1
            self.attempt_counters[curr_node_id] = 0
            self.nodes_visited +=1
            if next_node_id:
                self.current_node_id = next_node_id
                
    def info(self)->list[str]:
        info = [f"last node id: {self.current_node_id}, total visits: {self.nodes_visited}, flow_budget: {self.flow_budget}"]
        info += [f"Stat: Total errors: {len(self.errors)}, Total outputs: {len(self.outputs)}, Total params: {len(self.params)}"]
        if self.error_code or self.error_msg:
            info.append(f"Last error: {self.error_code if self.error_code else 'N/A'}{f"- {self.error_msg}" if self.error_msg else ''}")
        info.append("Attempts:")
        info += [f"{k}: {v}" for k, v in self.attempt_counters.items()]
        info.append("Visits:")
        info += [f"{k}: {v}" for k, v in self.visit_counters.items()]
        return info

    def info_errors(self)-> list[str]:
        if len(self.errors) == 0:
            return []
        errors = ["All errors in current workflow:"]
        return errors + [f"{k}: {v}" for k, v in self.errors.items()]

    def info_params(self)-> list[str]:
        if len(self.params) == 0:
            return []
        params = ["All parameters in current workflow:"]
        return params + [f"{k}: {v}" for k, v in self.params.items()]

    def info_outputs(self)-> list[str]:
        if len(self.outputs) == 0:
            return []
        outputs = ["All outputs in current workflow:"]
        return outputs + [f"{k}: {v}" for k, v in self.outputs.items()]

    def update(self, curr_node_id:str,save_as:str | None,output:ActionNodeOutput | None,next_node_id:str | None):
        self._update_cur_node(curr_node_id, output, save_as)
        self._update_stats(next_node_id, curr_node_id)

    def add_parameter(self, param_name:str, param_value:object):
        self.params[param_name] = ActionParameter.create(self.current_node_id, param_name, param_value)