from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from platformdirs import user_config_dir

from workflow_engine.tools import parameter_from_dict_default

CONFIG_FILE_NAME = "workflow_engine_config.json"


@dataclass(frozen=True)
class WorkflowEngineConfiguration:
    work_dir: str
    external_modules: tuple[str] = field(default_factory=tuple)
    storage: MappingProxyType[str, str] = field(default_factory=lambda: MappingProxyType({}))

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowEngineConfiguration:
        return WorkflowEngineConfiguration(
            work_dir=parameter_from_dict_default(data, "work_dir", str, "/"),
            external_modules=tuple(parameter_from_dict_default(data, "external_modules", list, [])),
            storage=MappingProxyType(parameter_from_dict_default(data, "storage", dict, {})),
        )


def _load_config(path: Path) -> WorkflowEngineConfiguration:
    import json

    with path.open() as f:
        data = json.load(f)
    return WorkflowEngineConfiguration.from_dict(data)


def load_configuration(config: WorkflowEngineConfiguration | None = None):
    if config is None:
        local_dir = Path(CONFIG_FILE_NAME)
        if not local_dir.exists():
            local_dir = Path(user_config_dir("workflow_engine")) / CONFIG_FILE_NAME
        config = _load_config(local_dir)
    return config
