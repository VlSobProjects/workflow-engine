from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from platformdirs import user_config_dir

from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.tools import parameter_from_dict_default

APPLICATION_DIRECTORY = ".workflow-engine"
CONFIG_FILE_NAME = "workflow_engine_config.json"
ENV_WORK_DIR = "WE_WORK_DIR"
ENV_STORAGE_DIR = "WE_STORAGE_DIR"
DEFAULT_HARD_MAX_NODES_VISITED = 1000


def _validated_hard_max_nodes_visited(value: int) -> int:
    # The hard cap has no "unlimited" value on purpose: it exists to bound runs whose soft limit
    # is 0. See ADR 010.
    if value < 1:
        raise WorkflowConfigurationError(f"hard_max_nodes_visited must be a positive integer, got: {value}")
    return value


@dataclass(frozen=True)
class WorkflowEngineConfiguration:
    work_dir: str = field(default=APPLICATION_DIRECTORY)
    external_modules: tuple[str] = field(default_factory=tuple)
    storage: MappingProxyType[str, str] = field(default_factory=lambda: MappingProxyType({}))
    hard_max_nodes_visited: int = field(default=DEFAULT_HARD_MAX_NODES_VISITED)

    def __post_init__(self) -> None:
        _validated_hard_max_nodes_visited(self.hard_max_nodes_visited)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowEngineConfiguration:
        return WorkflowEngineConfiguration(
            work_dir=parameter_from_dict_default(data, "work_dir", str, APPLICATION_DIRECTORY),
            external_modules=tuple(parameter_from_dict_default(data, "external_modules", list, [])),
            storage=MappingProxyType(parameter_from_dict_default(data, "storage", dict, {})),
            hard_max_nodes_visited=parameter_from_dict_default(
                data, "hard_max_nodes_visited", int, DEFAULT_HARD_MAX_NODES_VISITED
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "work_dir": self.work_dir,
            "external_modules": list(self.external_modules),
            "storage": dict(self.storage),
            "hard_max_nodes_visited": self.hard_max_nodes_visited,
        }


def _normalize_path(path_value: str | Path, base_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve(strict=False)


def _to_posix_string(path_value: str | Path | None, base_dir: Path) -> str:
    if path_value is None:
        raise ValueError("path value cannot be None")
    return _normalize_path(path_value, base_dir).as_posix()


def _resolve_config_search_path(explicit_path: Path | None, base_dir: Path, runtime_root: Path) -> Path:
    if explicit_path is not None:
        return _normalize_path(explicit_path, base_dir)

    local_config_path = base_dir / APPLICATION_DIRECTORY / CONFIG_FILE_NAME
    if local_config_path.exists():
        return local_config_path

    user_config_path = Path(user_config_dir()) / APPLICATION_DIRECTORY / CONFIG_FILE_NAME
    if user_config_path.exists():
        return user_config_path

    return runtime_root / CONFIG_FILE_NAME


def _resolve_runtime_root(base_dir: Path, work_dir_override: str | None, storage_dir_override: str | None) -> Path:
    if work_dir_override is not None:
        return _normalize_path(work_dir_override, base_dir)

    env_work_dir = os.getenv(ENV_WORK_DIR)
    if env_work_dir:
        return _normalize_path(env_work_dir, base_dir)

    if storage_dir_override is None:
        return base_dir / APPLICATION_DIRECTORY

    return base_dir / APPLICATION_DIRECTORY


def _resolve_work_dir(
    base_dir: Path,
    work_dir_override: str | None,
    storage_dir_override: str | None,
    config_data: dict[str, object],
) -> str:
    if work_dir_override is not None:
        return _to_posix_string(work_dir_override, base_dir)

    env_work_dir = os.getenv(ENV_WORK_DIR)
    if env_work_dir:
        return _to_posix_string(env_work_dir, base_dir)

    if storage_dir_override is None:
        config_work_dir = parameter_from_dict_default(config_data, "work_dir", str, None)
        if config_work_dir is not None:
            return _to_posix_string(config_work_dir, base_dir)

    return _to_posix_string(_resolve_runtime_root(base_dir, None, storage_dir_override), base_dir)


def _resolve_storage_dir(
    base_dir: Path,
    work_dir_value: Path,
    work_dir_override: str | None,
    storage_dir_override: str | None,
    config_data: dict[str, object],
) -> str:
    if storage_dir_override is not None:
        return _to_posix_string(storage_dir_override, base_dir)

    env_storage_dir = os.getenv(ENV_STORAGE_DIR)
    if env_storage_dir:
        return _to_posix_string(env_storage_dir, base_dir)

    if work_dir_override is not None or os.getenv(ENV_WORK_DIR):
        return work_dir_value.joinpath("json-storage").as_posix()

    config_storage = parameter_from_dict_default(config_data, "storage", dict, {})
    config_storage_dir = parameter_from_dict_default(config_storage, "storage_dir", str, None)
    if config_storage_dir is not None:
        return _to_posix_string(config_storage_dir, base_dir)

    return work_dir_value.joinpath("json-storage").as_posix()


def _load_config_data(path: Path) -> dict[str, object]:
    if path.is_file():
        try:
            with path.open() as f:
                return json.load(f)
        except json.JSONDecodeError as ex:
            raise WorkflowConfigurationError(f"Invalid JSON in config file: {path}") from ex
        except OSError as ex:
            raise WorkflowConfigurationError(f"Failed to read config file: {path}") from ex

    return {}


def _write_config(path: Path, config: WorkflowEngineConfiguration) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(config.to_dict(), f, indent=2)
    except OSError as ex:
        raise WorkflowConfigurationError(f"Failed to create config file: {path}") from ex


def load_config_file(
    path: Path | None = None,
    *,
    cwd: Path | None = None,
    work_dir_override: str | None = None,
    storage_dir_override: str | None = None,
) -> WorkflowEngineConfiguration:
    base_dir = cwd or Path.cwd()
    runtime_root = _resolve_runtime_root(base_dir, work_dir_override, storage_dir_override)
    resolved_config_path = _resolve_config_search_path(path, base_dir, runtime_root)

    config_data = _load_config_data(resolved_config_path)
    if not resolved_config_path.exists():
        resolved_config_path.parent.mkdir(parents=True, exist_ok=True)

    work_dir_value = Path(_resolve_work_dir(base_dir, work_dir_override, storage_dir_override, config_data))
    storage_dir_value = Path(
        _resolve_storage_dir(base_dir, work_dir_value, work_dir_override, storage_dir_override, config_data)
    )

    config = WorkflowEngineConfiguration(
        work_dir=work_dir_value.as_posix(),
        external_modules=tuple(parameter_from_dict_default(config_data, "external_modules", list, [])),
        storage=MappingProxyType({"storage_dir": storage_dir_value.as_posix()}),
        hard_max_nodes_visited=parameter_from_dict_default(
            config_data, "hard_max_nodes_visited", int, DEFAULT_HARD_MAX_NODES_VISITED
        ),
    )

    if not resolved_config_path.exists():
        _write_config(resolved_config_path, config)

    return config
