from workflow_engine.bootstrap.component_loader import ComponentLoader
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration, load_configuration
from workflow_engine.bootstrap.session_factory import WorkflowSessionsFactory
from workflow_engine.bootstrap.storage_fatcory import StorageFactory
from workflow_engine.engine import WorkflowEngine


class Bootstrap:
    config: WorkflowEngineConfiguration

    def __init__(self, config: WorkflowEngineConfiguration | None = None) -> None:
        self.config = load_configuration(config)

    def build_engine(self) -> WorkflowEngine:
        result = ComponentLoader(self.config).load_all()
        storage = StorageFactory(self.config).build_storage()
        s_factory = WorkflowSessionsFactory(self.config)
        return WorkflowEngine(storage, s_factory, result)
