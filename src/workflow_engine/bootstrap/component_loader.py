from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.bootstrap.plugin_external_modules import load_external_modules
from workflow_engine.bootstrap.plugin_manifest import ManifestPluginSource
from workflow_engine.registry.action_registry import get_registered_actions_info
from workflow_engine.registry.function_registry import get_registered_function_info, get_registered_validator_info
from workflow_engine.registry.type_registry import get_registered_codec_info


def dict_to_text(title: str, data: dict[str, str]) -> str:
    lines = [f"    {title}"]
    lines.extend(f"        - {k}: {v}" for k, v in data.items())
    return "\n".join(lines)


class ComponentLoader:
    def __init__(self, config: WorkflowEngineConfiguration) -> None:
        self.config = config

    def load_all(self) -> dict[str, dict[str, dict[str, str]]]:
        ManifestPluginSource.load_core_modules()
        result_core_actions = get_registered_actions_info()
        result_core_functions = get_registered_function_info()
        result_core_guards = get_registered_validator_info()
        result_core_codecs = get_registered_codec_info()
        load_external_modules(self.config.external_modules)
        result_external_actions = {
            key: value for key, value in get_registered_actions_info().items() if key not in result_core_actions
        }
        result_external_functions = {
            key: value for key, value in get_registered_function_info().items() if key not in result_core_functions
        }
        result_external_guards = {
            key: value for key, value in get_registered_validator_info().items() if key not in result_core_guards
        }
        result_external_codecs = {
            key: value for key, value in get_registered_codec_info().items() if key not in result_core_codecs
        }
        return {
            "Core components": {
                "Actions": result_core_actions,
                "Functions": result_core_functions,
                "Guards": result_core_guards,
                "Codecs": result_core_codecs,
            },
            "External components": {
                "Actions": result_external_actions,
                "Functions": result_external_functions,
                "Guards": result_external_guards,
                "Codecs": result_external_codecs,
            },
        }
