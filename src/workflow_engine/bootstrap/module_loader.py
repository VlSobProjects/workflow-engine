import importlib

from workflow_engine.exceptions import WorkflowConfigurationError


def load_modules(modules: tuple[str], source: str):
    for module_name in modules:
        try:
            if ":" in module_name:
                mod, fn = module_name.split(":", 1)
                obj = getattr(importlib.import_module(mod), fn)
                obj()
            else:
                importlib.import_module(module_name)
        except WorkflowConfigurationError as e:
            e.add_note(f"Component source: {source}, module: {module_name}")
            raise
        except (ModuleNotFoundError, ImportError, AttributeError) as e:
            raise WorkflowConfigurationError(
                f"Failed to load component: source={source}, module={module_name}, error={type(e).__name__}: {e}"
            ) from e
