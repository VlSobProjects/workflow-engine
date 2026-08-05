from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from inspect import getmro
from typing import Self, get_type_hints

from workflow_engine.exceptions import FunctionConfigurationError, FunctionRuntimeError
from workflow_engine.output import ActionNodeOutput
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_optional

FUNCTION_PARAMETERS_KEY = "function_parameters"
FUNCTION_NAME_KEY = "function_name"

type TFunc[T] = Callable[..., T]
type TDecorator[T] = Callable[[TFunc[T]], TFunc[T]]


FUNCTION_REGISTRY: dict[str, RegisteredFunction] = {}
VALIDATOR_REGISTRY: dict[str, RegisteredValidator] = {}


@dataclass(slots=True)
class BaseRegisteredFunction[T](ABC):
    name: str
    signature: inspect.Signature
    hints: dict[str, object]
    function: Callable[..., T]
    args_cleaner: Callable[[dict[str, object]], dict[str, object]]

    def check_args(self, args: dict[str, object] | None) -> None:
        bound_args = self.args_cleaner(args) if args is not None else {}
        try:
            _ = self.signature.bind(**bound_args)
        except TypeError as e:
            ex = FunctionConfigurationError(
                function_name=self.name, parameters=bound_args, message="signature.bind failed"
            )
            ex.add_note(f"Function signature: {self.signature.parameters.__repr__()}")
            raise ex from e

    def check_function_return_type(self) -> None:
        r_type = self.hints.get("return")
        if r_type is None:
            raise FunctionConfigurationError(
                function_name=self.name, parameters=None, message="Function return type is not specified in type hints"
            )
        if self.hints["return"] != self.get_expected_type():
            raise FunctionConfigurationError(
                function_name=self.name,
                parameters=None,
                message=f"Function return type is incorrect. "
                f"Expected: {self.get_expected_type().__name__}, "
                f"got: {r_type.__repr__()}",
            )

    @classmethod
    def factory(
        cls, name: str, signature: inspect.Signature, hints: dict[str, object], function: Callable[..., T]
    ) -> Self:
        if cls == BaseRegisteredFunction:
            raise TypeError("BaseRegisteredFunction cannot be instantiated directly. Use a subclass.")

        def arg_c(data: dict[str, object]) -> dict[str, object]:
            return {k: v for k, v in data.items() if k in signature.parameters}

        return cls(name=name, signature=signature, hints=hints, function=function, args_cleaner=arg_c)

    @abstractmethod
    def get_expected_type(self) -> type[T]:
        pass


@dataclass(slots=True)
class RegisteredFunction(BaseRegisteredFunction[ActionNodeOutput]):
    """Function output type is NodeOutput"""

    def get_expected_type(self) -> type[ActionNodeOutput]:
        return ActionNodeOutput


@dataclass(slots=True)
class RegisteredValidator(BaseRegisteredFunction[bool]):
    """Validator output type is boolean"""

    def get_expected_type(self) -> type[bool]:
        return bool


def _register[T](
    func: Callable[..., T],
    registry: dict[str, BaseRegisteredFunction[T]],
    register_type: type[BaseRegisteredFunction[T]],
):
    func_name = func.__name__
    if func_name in registry:
        raise ValueError(f"Function '{func_name}' is already registered")
    signature = inspect.signature(func)

    registered_function = register_type.factory(
        name=func_name,
        function=func,
        signature=signature,
        hints=get_type_hints(func, include_extras=True),
    )
    registered_function.check_function_return_type()
    registry[func.__name__] = registered_function


def _reg[T](
    func: TFunc[T] | None,
    registry: dict[str, BaseRegisteredFunction[T]],
    register_type: type[BaseRegisteredFunction[T]],
    decorators: Sequence[TDecorator[T]],
):
    def decorator(d_func: TFunc[T]) -> TFunc[T]:
        wrapped: TFunc[T] = d_func

        for d in reversed(decorators):
            wrapped = d(wrapped)

        _register(wrapped, registry, register_type)

        return wrapped

    if func is None:
        return decorator

    return decorator(func)


def register_function(
    func: TFunc[ActionNodeOutput] | None = None,
    *,
    decorators: Sequence[TDecorator[ActionNodeOutput]] = (),
):
    return _reg(func, FUNCTION_REGISTRY, RegisteredFunction, decorators)


def register_validator(
    func: TFunc[bool] | None = None,
    *,
    decorators: Sequence[TDecorator[bool]] = (),
):
    return _reg(func, VALIDATOR_REGISTRY, RegisteredValidator, decorators)


@dataclass(slots=True)
class RegisteredFunctionExecutor[T]:
    registered_function: BaseRegisteredFunction[T]
    parameters: dict[str, object] | None

    def execute(self, parameters_modified: Callable[[dict[str, object]], dict[str, object]] | None = None) -> T:
        params = self.parameters
        if self.parameters is not None and parameters_modified is not None:
            params = parameters_modified(self.parameters)
        elif parameters_modified is not None:
            params = parameters_modified({})

        try:
            if params is not None:
                return self.registered_function.function(**self.registered_function.args_cleaner(params))
            else:
                return self.registered_function.function()
        except Exception as e:
            raise FunctionRuntimeError(
                function_name=self.registered_function.name,
                parameters=params,
                message=f"Error executing registered function: {e}",
            ) from e


def _get_registered_executor[T](
    registry: dict[str, BaseRegisteredFunction[T]], name: str, parameters: dict[str, object] | None = None
) -> RegisteredFunctionExecutor[T]:
    registered_function = registry.get(name)
    if registered_function is None:
        raise FunctionConfigurationError(
            function_name=name,
            parameters=parameters,
            message=f"Function '{name}' is not registered",
        )
    return RegisteredFunctionExecutor(registered_function=registered_function, parameters=parameters)


def get_registered_function[T](
    requested_class: type,
    executor_return: type[T],
    data: dict[str, object],
    addition_parameters: dict[str, object] | None = None,
) -> RegisteredFunctionExecutor[T]:
    """Get a registered function or validator based on the requested class and data."""
    from workflow_engine.actions.base_actions import BaseAction
    from workflow_engine.transition.guards import BaseGuard

    f_name = parameter_from_dict(data, FUNCTION_NAME_KEY, str)
    params = parameter_from_dict_optional(data, FUNCTION_PARAMETERS_KEY, dict)
    func_ex: RegisteredFunctionExecutor[T]
    # Determine which registry to use based on the requested class.
    # guard request function from wrong class
    if BaseAction in getmro(requested_class):
        func_ex = _get_registered_executor(FUNCTION_REGISTRY, f_name, params)
    elif BaseGuard in getmro(requested_class):
        func_ex = _get_registered_executor(VALIDATOR_REGISTRY, f_name, params)
    else:
        raise FunctionConfigurationError(
            function_name=f_name,
            parameters=params,
            message=f"Function {type(requested_class).__name__} is not allowed to use registered functions",
        )
    if addition_parameters is not None:
        if params is None:
            params = addition_parameters
        else:
            params.update(addition_parameters)

    # check if return type of function is same as requested
    if executor_return != func_ex.registered_function.get_expected_type():
        raise FunctionConfigurationError(
            function_name=f_name,
            parameters=params,
            message=f"Function '{f_name}' return type is not compatible with expected type {executor_return.__name__}",
        )

    # check function parameters in configuration time
    func_ex.registered_function.check_args(params)
    return func_ex


def get_registered_function_info() -> dict[str, str]:
    return {key: ex.function.__doc__ or "N/A" for key, ex in FUNCTION_REGISTRY.items()}


def get_registered_validator_info() -> dict[str, str]:
    return {key: ex.function.__doc__ or "N/A" for key, ex in VALIDATOR_REGISTRY.items()}
