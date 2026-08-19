"""Decorators that validate the arguments of a registered function before it runs.

A path argument accepts a string or a ``pathlib.Path``: the engine resolves ``param.<name>`` to the
typed value a codec restored, so an input declared with ``type: Path`` reaches the function as a
``Path``, and every one of these functions builds a ``Path`` from it as its first act anyway.
"""

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Final

from workflow_engine.exceptions import FunctionRuntimeError

PATH_TYPES: Final[tuple[type, ...]] = (str, Path)

_MISSING: Final[object] = object()


def _argument_value(name: str, index: int, args: tuple[object, ...], kwargs: dict[str, object]) -> object:
    if name in kwargs:
        return kwargs[name]
    if index < len(args):
        return args[index]
    return _MISSING


def _accepted_names(accepted: tuple[type, ...]) -> str:
    return " or ".join(f"'{accepted_type.__name__}'" for accepted_type in accepted)


def _check_args(
    function_name: str,
    accepted: tuple[type, ...],
    on_validation_failed: str,
    checker: Callable[[str | Path], bool],
    chek_ars: dict[str, int],
    args: tuple[object, ...],
    kwargs: dict[str, object],
):
    errors: dict[str, str] = {}
    for arg, index in chek_ars.items():
        value = _argument_value(arg, index, args, kwargs)
        if value is _MISSING:
            # An argument the call does not carry is not this validator's business: either the
            # signature has a default for it, or binding fails before the function body runs.
            continue
        if not isinstance(value, accepted):
            errors[arg] = f"Argument {value.__str__()} is not {_accepted_names(accepted)}"
        elif not checker(value):
            errors[arg] = f"Argument {value.__str__()} - validation '{on_validation_failed}' failed."
    if len(errors) > 0:
        # The failures are the message: the parameters slot reports what the call was given, not
        # what was wrong with it.
        raise FunctionRuntimeError(
            function_name=function_name,
            message="; ".join(f"{argument}: {problem}" for argument, problem in errors.items()),
        )


def not_empty_str_arg_validator(chek_ars: dict[str, int]):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate the arguments before calling the function
            _check_args(func.__name__, (str,), "not empty", lambda x: len(x) > 0, chek_ars, args=args, kwargs=kwargs)
            return func(*args, **kwargs)

        return wrapper

    return inner


def folder_exists_arg_validator(chek_ars: dict[str, int]):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate the arguments before calling the function
            _check_args(
                func.__name__,
                PATH_TYPES,
                "folder exists",
                lambda x: Path(x).is_dir(),
                chek_ars,
                args=args,
                kwargs=kwargs,
            )
            return func(*args, **kwargs)

        return wrapper

    return inner


def file_exists_arg_validator(chek_ars: dict[str, int]):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate the arguments before calling the function
            _check_args(
                func.__name__,
                PATH_TYPES,
                "file exists",
                lambda x: Path(x).is_file(),
                chek_ars,
                args=args,
                kwargs=kwargs,
            )
            return func(*args, **kwargs)

        return wrapper

    return inner
