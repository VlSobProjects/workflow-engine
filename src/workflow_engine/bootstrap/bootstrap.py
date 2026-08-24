from workflow_engine.bootstrap.component_loader import ComponentLoader
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.bootstrap.session_factory import WorkflowSessionsFactory
from workflow_engine.bootstrap.storage_fatcory import StorageFactory
from workflow_engine.engine import WorkflowEngine
from workflow_engine.providers.provider_seat import install_provider_settings


class Bootstrap:
    config: WorkflowEngineConfiguration

    def __init__(self, config: WorkflowEngineConfiguration) -> None:
        self.config = config

    def build_engine(self) -> WorkflowEngine:
        result = ComponentLoader(self.config).load_all()
        # The adapters are registered by the loading above; the seat can only be installed after it.
        install_provider_settings(self.config.providers)
        storage_factory = StorageFactory(self.config)
        s_factory = WorkflowSessionsFactory(self.config)
        return WorkflowEngine(
            storage_factory, s_factory, result, self.config.hard_max_nodes_visited, self.config.export_dir
        )
