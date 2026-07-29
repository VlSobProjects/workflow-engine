from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from workflow_engine.exceptions import RuntimeParameterError


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

    def update_on_submit(self, next_node_id: str, output: str, param_name: str | None=None, param_value: object | None=None):
        self.outputs[self.current_node_id] = output
        self.nodes_visited += 1
        if self.current_node_id == next_node_id:
            #update attempt_counters if second attempt
            self.attempt_counters[next_node_id] += 1
        else:
            # reset attempt_counters and update visit_counters
            self.attempt_counters[self.current_node_id] = 0
            if next_node_id not in self.visit_counters:
                self.visit_counters[next_node_id] = 1
            else: self.visit_counters[next_node_id] += 1
            self.current_node_id = next_node_id

        if param_name is not None and param_value is not None:
            self.params[param_name] = ActionParameter(
                source_node_id=self.current_node_id,
                name=param_name,
                value=param_value
            )

    def set_error(self,output: str, errors: list[str]):
        output_parts = output.split(";")
        if output_parts[0] in errors:
            if len(output_parts) >= 2:
                self.error_code = output_parts[0]
                self.error_msg = output_parts[1]
            else:
                self.error_code = output
                self.error_msg = "Unknown error"