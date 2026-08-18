from workflow_engine.bootstrap.component_loader import ComponentLoader
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.bootstrap.session_factory import WorkflowSessionsFactory
from workflow_engine.bootstrap.storage_fatcory import StorageFactory
from workflow_engine.engine import WorkflowEngine


class Bootstrap:
    config: WorkflowEngineConfiguration

    def __init__(self, config: WorkflowEngineConfiguration) -> None:
        self.config = config

    def build_engine(self) -> WorkflowEngine:
        result = ComponentLoader(self.config).load_all()
        storage_factory = StorageFactory(self.config)
        s_factory = WorkflowSessionsFactory(self.config)
        return WorkflowEngine(
            storage_factory, s_factory, result, self.config.hard_max_nodes_visited, self.config.export_dir
        )
