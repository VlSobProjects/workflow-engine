from pathlib import Path
from types import MappingProxyType

from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.storage.json_storage import JsonStorage
from workflow_engine.storage.storage import Storage
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_default

JSON_STORAGE_FOLDER_KEY = "storage_dir"
JSON_STORAGE_FOLDER_DEFAULT = "json-storage"


class StorageFactory:
    def __init__(self, config: WorkflowEngineConfiguration):
        self.config = config

    def storage_config(self) -> MappingProxyType[str, str]:
        return MappingProxyType(
            {
                JSON_STORAGE_FOLDER_KEY: parameter_from_dict_default(
                    self.config.storage,
                    JSON_STORAGE_FOLDER_KEY,
                    str,
                    self.config.work_dir + "/" + JSON_STORAGE_FOLDER_DEFAULT,
                )
            }
        )

    @classmethod
    def build_storage(cls, storage_config: MappingProxyType[str, str]) -> Storage:
        return JsonStorage(Path(parameter_from_dict(storage_config, JSON_STORAGE_FOLDER_KEY, str)))
