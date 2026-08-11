from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from workflow_engine.tools import parameter_from_dict_default

APPLICATION_DIRECTORY = ".workflow-engine"
CONFIG_FILE_NAME = "workflow_engine_config.json"


@dataclass(frozen=True)
class WorkflowEngineConfiguration:
    work_dir: str = field(default=APPLICATION_DIRECTORY)
    external_modules: tuple[str] = field(default_factory=tuple)
    storage: MappingProxyType[str, str] = field(default_factory=lambda: MappingProxyType({}))

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowEngineConfiguration:
        return WorkflowEngineConfiguration(
            work_dir=parameter_from_dict_default(data, "work_dir", str, APPLICATION_DIRECTORY),
            external_modules=tuple(parameter_from_dict_default(data, "external_modules", list, [])),
            storage=MappingProxyType(parameter_from_dict_default(data, "storage", dict, {})),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "work_dir": self.work_dir,
            "external_modules": list(self.external_modules),
            "storage": dict(self.storage),
        }


def _load_config(path: Path) -> WorkflowEngineConfiguration:
    import json

    if path.is_file():
        with path.open() as f:
            data = json.load(f)
        return WorkflowEngineConfiguration.from_dict(data)
    else:
        config = WorkflowEngineConfiguration()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(config.to_dict(), f)

    return config


def load_config_file(path: Path | None) -> WorkflowEngineConfiguration:
    if path is None:
        path = Path(APPLICATION_DIRECTORY) / CONFIG_FILE_NAME
    return _load_config(path)
