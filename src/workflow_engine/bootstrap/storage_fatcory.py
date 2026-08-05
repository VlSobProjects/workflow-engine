from pathlib import Path

from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.storage.json_storage import JsonStorage
from workflow_engine.storage.storage import Storage
from workflow_engine.tools import parameter_from_dict_default

JSON_STORAGE_FOLDER_KEY = "storage_dir"
JSON_STORAGE_FOLDER_DEFAULT = "storage"


class StorageFactory:
    def __init__(self, config: WorkflowEngineConfiguration):
        self.config = config

    def build_storage(self) -> Storage:
        return JsonStorage(
            Path(
                parameter_from_dict_default(
                    self.config.storage,
                    JSON_STORAGE_FOLDER_KEY,
                    str,
                    self.config.work_dir + "/" + JSON_STORAGE_FOLDER_DEFAULT,
                )
            )
        )
