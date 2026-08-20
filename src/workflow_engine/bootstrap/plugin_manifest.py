from workflow_engine.bootstrap.module_loader import load_modules

CORE_MODULES = [
    "workflow_engine.actions.base_functions",
    "workflow_engine.actions.action_nodes",
    "workflow_engine.actions.action_ask",
    "workflow_engine.codecs.base_codecs",
    "workflow_engine.validators.output_function_validators",
    "workflow_engine.actions.file_info_functions",
    "workflow_engine.actions.create_artifact_functions",
    "workflow_engine.actions.modify_param_functions",
    "workflow_engine.actions.answer_functions",
]


class ManifestPluginSource:
    @classmethod
    def load_core_modules(cls):
        load_modules(tuple(CORE_MODULES), source="Core components")
