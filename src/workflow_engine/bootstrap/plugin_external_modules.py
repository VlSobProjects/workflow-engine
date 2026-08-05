from workflow_engine.bootstrap.module_loader import load_modules


def load_external_modules(external_modules: tuple[str]):
    load_modules(external_modules, source="External components")
