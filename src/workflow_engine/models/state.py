from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal, final

from workflow_engine.exceptions import (
    ArtifactPathError,
    StateLoadError,
    StateLoadParameterError,
    WorkflowParameterError,
    WorkflowRuntimeError,
)
from workflow_engine.output import ActionNodeOutput, ParamWrite, WorkflowArtifact, WriteParamMode
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

PARAM_OVERWRITE_FORBIDDEN = "param_overwrite_forbidden"
ARTIFACT_OVERWRITE = "artifact_overwritten"
ARTIFACT_PATH_CONFLICT = "artifact_path_conflict"
INVALID_WRITE_MODE = "invalid_write_mode"
PARAM_TYPE_MISMATCH = "param_type_mismatch"


class SessionEventCode(Enum):
    SESSION_CREATED = "session_created"
    WORKFLOW_STARTED = "workflow_started"
    OPERATOR_LIMIT_UPDATED = "operator_limit_updated"
    WORKFLOW_RESUMED = "workflow_resumed"
    WORKFLOW_PAUSED_LIMIT = "workflow_paused_limit"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"


OPERATOR_CODES = (
    SessionEventCode.SESSION_CREATED,
    SessionEventCode.OPERATOR_LIMIT_UPDATED,
    SessionEventCode.WORKFLOW_RESUMED,
    SessionEventCode.WORKFLOW_STARTED,
)

ENGINE_CODES = (
    SessionEventCode.WORKFLOW_PAUSED_LIMIT,
    SessionEventCode.WORKFLOW_COMPLETED,
    SessionEventCode.WORKFLOW_FAILED,
)


@dataclass(frozen=True, slots=True)
class SessionEvent:
    timestamp: datetime
    code: str
    actor: Literal["engine", "operator"]
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    details: str | None = field(default=None)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SessionEvent:
        event_id = parameter_from_dict(data, "event_id", str)
        actor = "engine" if parameter_from_dict(data, "actor", str) == "engine" else None
        if actor is None:
            actor = "operator" if parameter_from_dict(data, "actor", str) == "operator" else None
        if actor is None:
            raise StateLoadParameterError(
                current_node="ANY",
                parameter_name="SessionEvent.actor",
                message=f"Session Event: {event_id} Invalid actor value: {parameter_from_dict(data, 'actor', str)}, "
                f"allowed values: ('engine', 'operator')",
            )
        return cls(
            timestamp=datetime.fromisoformat(parameter_from_dict(data, "timestamp", str)),
            code=parameter_from_dict(data, "code", str),
            actor=actor,
            event_id=event_id,
            details=parameter_from_dict_optional(data, "details", str),
        )

    def to_dict(self) -> dict[str, object]:
        d = {
            "timestamp": self.timestamp.isoformat(),
            "code": self.code,
            "actor": self.actor,
            "event_id": self.event_id,
        }
        if self.details is not None:
            d["details"] = self.details
        return d

    @classmethod
    def operator_event(cls, code: SessionEventCode, details: str | None = None) -> SessionEvent:
        if code not in OPERATOR_CODES:
            raise WorkflowRuntimeError(
                f"{code} is not a valid session event code for operator. valid codes: {OPERATOR_CODES} "
            )
        return cls(timestamp=datetime.now(tz=UTC), code=code.value, actor="operator", details=details)

    @classmethod
    def engine_event(cls, code: SessionEventCode, details: str | None = None) -> SessionEvent:
        if code not in ENGINE_CODES:
            raise WorkflowRuntimeError(
                f"{code} is not a valid session event code for engine. valid codes: {ENGINE_CODES} "
            )
        return cls(timestamp=datetime.now(tz=UTC), code=code.value, actor="engine", details=details)


@dataclass(frozen=True)
class ArtifactEvent:
    code: str  # "artifact_overwritten"
    node_id: str
    logical_name: str
    relative_path: Path
    timestamp: datetime
    message: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ArtifactEvent:
        return cls(
            code=parameter_from_dict(data, "code", str),
            node_id=parameter_from_dict(data, "node_id", str),
            logical_name=parameter_from_dict(data, "logical_name", str),
            relative_path=Path(parameter_from_dict(data, "relative_path", str)),
            timestamp=datetime.fromisoformat(parameter_from_dict(data, "timestamp", str)),
            message=parameter_from_dict_optional(data, "message", str),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "node_id": self.node_id,
            "logical_name": self.logical_name,
            "relative_path": self.relative_path.as_posix(),
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
        }

    @classmethod
    def overwritten(cls, node_id, name: str, old: WorkflowArtifact, new: WorkflowArtifact) -> ArtifactEvent:
        return cls(
            code=ARTIFACT_OVERWRITE,
            node_id=node_id,
            logical_name=name,
            relative_path=new.relative_path,
            timestamp=new.created_at,
            message=f"Artifact '{name}' overwritten. "
            f"Old: {old.description if old.description else 'N/A'}, "
            f"New: {new.description if new.description else 'N/A'}",
        )

    @classmethod
    def path_conflict(
        cls, node_id, new_name: str, old_name: str, old: WorkflowArtifact, new: WorkflowArtifact
    ) -> ArtifactEvent:
        return cls(
            code=ARTIFACT_PATH_CONFLICT,
            node_id=node_id,
            logical_name=new_name,
            relative_path=new.relative_path,
            timestamp=new.created_at,
            message=f"Artifact 'path conflict with. "
            f"Old - '{old_name}': {old.description if old.description else 'N/A'}, "
            f"New - '{new_name}': {new.description if new.description else 'N/A'}",
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


@final
@dataclass(frozen=True, slots=True)
class StateReadOnlyView:
    _get_param_fn: Final[Callable[[str, object], object | None]]
    _get_output_fn: Final[Callable[[str], str | None]]
    _outputs_fn: Final[Callable[[], MappingProxyType[str, str]]]
    _set_parameters: Final[Callable[[dict[str, object], dict[str, object] | None], dict[str, object]]]
    _is_artifact_exist_by_name: Final[Callable[[str], bool]]
    _is_artifact_exist_by_path: Final[Callable[[Path], bool]]
    work_dir: Path

    @classmethod
    def from_state(cls, state: StateModel) -> StateReadOnlyView:
        def get_param(name: str, default: object = None) -> object | None:
            value = state.get_param(name)
            if value is None:
                return default
            return deepcopy(value)

        def get_output(node_id: str) -> str | None:
            return state.outputs.get(node_id)

        def outputs() -> MappingProxyType[str, str]:
            return MappingProxyType(dict(state.outputs))

        def set_parameters(params: dict[str, object], options: dict[str, object] | None = None) -> dict[str, object]:
            return state.set_parameters(params, options)

        def is_artifact_exist_by_name(name: str) -> bool:
            return name in state.artifacts

        def is_artifact_exist_by_path(relative_path: Path) -> bool:
            return any(artifact.relative_path == relative_path for artifact in state.artifacts.values())

        return cls(
            get_param,
            get_output,
            outputs,
            set_parameters,
            is_artifact_exist_by_name,
            is_artifact_exist_by_path,
            work_dir=state.work_dir,
        )

    def get_param(self, name: str, default: object = None) -> object | None:
        return self._get_param_fn(name, default)

    def get_output(self, node_id: str) -> str | None:
        return self._get_output_fn(node_id)

    def outputs(self) -> MappingProxyType[str, str]:
        return self._outputs_fn()

    def set_parameters(self, params: dict[str, object], options: dict[str, object] | None = None) -> dict[str, object]:
        return self._set_parameters(params, options)

    def set_parameters_with_updater(
        self, updater: dict[str, object]
    ) -> Callable[[dict[str, object]], dict[str, object]]:
        return lambda parameters: self.set_parameters(parameters, updater)

    def get_work_dir(self) -> Path:
        return self.work_dir

    def is_artifact_exist_by_name(self, name: str) -> bool:
        return self._is_artifact_exist_by_name(name)

    def is_artifact_exist_by_path(self, relative_path: Path) -> bool:
        return self._is_artifact_exist_by_path(relative_path)

    def _resolve_artifact_path(self, path: str | Path) -> tuple[Path, Path]:
        artifacts_root = (self.work_dir / "artifacts").resolve()
        target = Path(path)
        absolute_path = target.resolve() if target.is_absolute() else (artifacts_root / target).resolve()
        try:
            relative_path = absolute_path.relative_to(artifacts_root)
        except ValueError as ex:
            raise ArtifactPathError(
                path=target.as_posix(),
                artifacts_root=artifacts_root.as_posix(),
                message="Artifact path must resolve inside work_dir/artifacts",
            ) from ex
        if relative_path == Path():
            raise ArtifactPathError(
                path=target.as_posix(),
                artifacts_root=artifacts_root.as_posix(),
                message="Artifact path points to artifacts root; file path expected",
            )
        return absolute_path, relative_path

    def get_artifact_absolute_path(self, path: str | Path) -> Path:
        absolute_path, _ = self._resolve_artifact_path(path)
        return absolute_path

    def get_artifact_relative_path(self, path: str | Path) -> Path:
        _, relative_path = self._resolve_artifact_path(path)
        return relative_path


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
    artifacts: dict[str, WorkflowArtifact] = field(default_factory=dict)
    artifact_events: list[ArtifactEvent] = field(default_factory=list)  # folder in workdir with files
    session_events: list[SessionEvent] = field(default_factory=list)
    max_nodes_visited: int = field(default=0)  # engine-managed params: _flow_budget (int)
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
            params["artifact_events"] = [
                ArtifactEvent.from_dict(v) for v in parameter_from_dict_default(data, "artifact_events", list, [])
            ]
            params["session_events"] = [
                SessionEvent.from_dict(v) for v in parameter_from_dict_default(data, "session_events", list, [])
            ]
            guard_results = parameter_from_dict_default(data, "guard_results", dict, {})
            params["guard_results"] = {
                k: GuardRecord.from_list(parameter_from_dict_default(guard_results, str(k), list, []))
                for k in guard_results
            }
            params["artifacts"] = {
                k: WorkflowArtifact.from_dict(v)
                for k, v in parameter_from_dict_default(data, "artifacts", dict, {}).items()
            }
            params["max_nodes_visited"] = parameter_from_dict_default(data, "max_nodes_visited", int, 0)
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

    def is_max_node_exceeded(self) -> bool:
        return self.max_nodes_visited != 0 and self.nodes_visited >= self.max_nodes_visited

    def has_session_event(self, code: SessionEventCode) -> bool:
        return any(event.code == code.value for event in self.session_events)

    def record_session_event(self, event: SessionEvent) -> None:
        self.session_events.append(event)

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
            f"last node id: {self.current_node_id}, total visits: {self.nodes_visited}, "
            f"flow_budget: {self.max_nodes_visited}"
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
                error = self._param_write(param_name, param_write)
                if error is not None:
                    self.error_code, self.error_msg = error
                    output.error_code, output.error_msg = error
                    self.errors[curr_node_id] = f"[{self.error_code}] {self.error_msg}"
                    break

        self._set_artifacts(output)

    def add_parameter(self, param_name: str, param_value: object):
        self.params[param_name] = ActionParameter.create(self.current_node_id, param_name, param_value)

    def _param_write(self, param_name: str, param_write: ParamWrite) -> tuple[str, str] | None:
        from workflow_engine.collection_param_handlers import MODIFY_GROUP, modify_param_object

        if param_name in self.params:
            if param_write.mode in MODIFY_GROUP:
                result = modify_param_object(
                    self.params[param_name].value, param_name, param_write.mode, param_write.value
                )
                if result.error_code is not None and result.error_msg is not None:
                    return result.error_code, result.error_msg
                else:
                    self.params[param_name].value = result.collection
            elif param_write.allow_overwrite or param_write.mode == WriteParamMode.REPLACE:
                self.params[param_name].value = param_write.value
            else:
                return (
                    PARAM_OVERWRITE_FORBIDDEN,
                    f"Cannot set parameter '{param_name}' with mode '{param_write.mode}' "
                    f"allow_overwrite={param_write.allow_overwrite}",
                )
        elif param_write.mode == WriteParamMode.SET:
            self.params[param_name] = ActionParameter.create(self.current_node_id, param_name, param_write.value)
        elif param_write.mode == WriteParamMode.REPLACE:
            return (
                INVALID_WRITE_MODE,
                f"Cannot replace parameter '{param_name}' parameter is not exist in workflow params' ",
            )
        else:
            return (
                INVALID_WRITE_MODE,
                f"Cannot modify '{param_name}' parameter mode: {param_write.mode} "
                "as it does not exist in workflow params' ",
            )

        return None

    def _get_artifact_by_path(self, relative_path: Path) -> tuple[str, WorkflowArtifact] | None:
        for artifact_name, artifact in self.artifacts.items():
            if artifact.relative_path.absolute() == relative_path.absolute():
                return artifact_name, artifact
        return None

    def _set_artifacts(self, output: ActionNodeOutput | None):
        if output is not None and len(output.artifacts) > 0:
            for artifact_name, artifact in output.artifacts.items():
                if artifact_name in self.artifacts:
                    old_artifact = self.artifacts[artifact_name]
                    self.artifact_events.append(
                        ArtifactEvent.overwritten(self.current_node_id, artifact_name, old_artifact, artifact)
                    )
                else:
                    path_conflict_artifact = self._get_artifact_by_path(artifact.relative_path)

                    if path_conflict_artifact is not None:
                        self.artifacts.pop(path_conflict_artifact[0])
                        self.artifact_events.append(
                            ArtifactEvent.path_conflict(
                                self.current_node_id,
                                artifact_name,
                                path_conflict_artifact[0],
                                path_conflict_artifact[1],
                                artifact,
                            )
                        )
                self.artifacts[artifact_name] = artifact
