from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TypeVar

from workflow_engine.output import ActionNodeOutput

T = TypeVar("T",str,int)


def _check_args[T](check_type:type[T],checker:Callable[[T],bool],chek_ars:dict[str,int],args:tuple[object], kwargs:dict[str,object]) -> list[str]:
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
            errors.append(f"Argument '{arg}'='{value.__str__()}' - validation failed.")
    return errors


def not_empty_str_arg_validator(chek_ars:dict[str,int]):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print("VALIDATOR CALLED")
            # Validate the arguments before calling the function
            errors: list[str] = _check_args(str, lambda x: len(x) > 0, chek_ars, args=args, kwargs=kwargs)
            if errors:
                raise ValueError(f"Parameters validation failed for function '{func.__name__}': " + "; ".join(errors))
            else:
                return func(*args, **kwargs)
        return wrapper
    return inner


def action_file_exists_arg_validator(chek_ars:dict[str,int]):
    def inner(func):
        def wrapper(*args, **kwargs)->ActionNodeOutput:
            # Validate the arguments before calling the function
            errors: list[str] = _check_args(str, lambda x: Path(x).is_file(), chek_ars, args=args, kwargs=kwargs)
            if errors:
                return ActionNodeOutput(
                    output=f"Parameters validation failed for function '{func.__name__}'",
                    error_code="file_not_found",
                    error_message="; ".join(errors)
                )
            else:
                return func(*args, **kwargs)
        return wrapper
    return inner