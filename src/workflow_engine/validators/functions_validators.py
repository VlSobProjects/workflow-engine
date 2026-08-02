from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TypeVar

from workflow_engine.exceptions import FunctionArgsError

T = TypeVar("T", str, int)


def _check_args[T](
    function_name: str,
    check_type: type[T],
    on_validation_failed: str,
    checker: Callable[[T], bool],
    chek_ars: dict[str, int],
    args: tuple[object],
    kwargs: dict[str, object],
):
    errors: list[str] = []
    value = None
    for arg, index in chek_ars.items():
        if arg in kwargs:
            value = kwargs[arg]
        elif index < len(args):
            value = args[index]
        if not isinstance(value, check_type):
            errors.append(f"Argument '{arg}'={value.__str__()} is not a '{check_type.__name__}'")
        elif not checker(value):
            errors.append(f"Argument '{arg}'='{value.__str__()}' - validation '{on_validation_failed}' failed.")
    if len(errors) > 0:
        raise FunctionArgsError(function_name, errors)


def not_empty_str_arg_validator(chek_ars: dict[str, int]):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate the arguments before calling the function
            _check_args(func.__name__, str, "not empty", lambda x: len(x) > 0, chek_ars, args=args, kwargs=kwargs)
            return func(*args, **kwargs)

        return wrapper

    return inner


def folder_exists_arg_validator(chek_ars: dict[str, int]):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate the arguments before calling the function
            _check_args(
                func.__name__, str, "folder exists", lambda x: Path(x).is_dir(), chek_ars, args=args, kwargs=kwargs
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
                func.__name__, str, "file exists", lambda x: Path(x).is_file(), chek_ars, args=args, kwargs=kwargs
            )
            return func(*args, **kwargs)

        return wrapper

    return inner
