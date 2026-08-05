from workflow_engine.bootstrap.module_loader import load_modules

CORE_MODULES = [
    "workflow_engine.actions.base_functions",
    "workflow_engine.actions.action_nodes",
    "workflow_engine.codecs.base_codecs",
    "workflow_engine.validators.output_function_validators",
]


class ManifestPluginSource:
    @classmethod
    def load_core_modules(cls):
        load_modules(tuple(CORE_MODULES), source="Core components")
