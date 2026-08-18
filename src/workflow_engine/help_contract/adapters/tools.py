from typing import Annotated, get_args, get_origin, ClassVar

from workflow_engine.registry.function_registry import RegisteredFunction, RegisteredValidator


def is_class_var(annotation: object) -> bool:
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]

    return get_origin(annotation) is ClassVar

def unwrap_annotation(annotation: type) -> tuple[type, str]:
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)

        annotation = args[0]

        for metadata in args[1:]:
            if isinstance(metadata, str):
                return annotation, metadata

    return annotation, "N/A"

def get_function_args(function: RegisteredFunction | RegisteredValidator) -> dict[str, tuple[type, str]]:
    """Get the arguments of a function as a dictionary."""
    parameters: dict[str, tuple[type, str]] = {}
    for name, param in function.signature.parameters.items():
        t,description = unwrap_annotation(param.annotation)

        parameters[name] = (t, description or "N/A")

    return parameters