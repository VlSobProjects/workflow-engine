from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from types import UnionType
from typing import Self, TypeVar, get_type_hints

from workflow_engine.exceptions import FunctionParametersTypeError
from workflow_engine.output import ActionNodeOutput

FUNCTION_PARAMETERS_KEY = "function_parameters"
FUNCTION_NAME_KEY = "function_name"

T = TypeVar("T", str, bool, str | None, ActionNodeOutput)

type TFunc[T] = Callable[..., T]
type TDecorator[T] = Callable[[TFunc[T]], TFunc[T]]


# type ActionNodeOutputFunc = Callable[..., ActionNodeOutput]
# type ActionNodeOutputDecorator = Callable[[ActionNodeOutputFunc], ActionNodeOutput]


FUNCTION_REGISTRY: dict[str, RegisteredFunction] = {}
VALIDATOR_REGISTRY: dict[str, RegisteredValidator] = {}
TRANSACTION_REGISTRY: dict[str, RegisteredTransaction] = {}


@dataclass(slots=True)
class BaseRegisteredFunction[T](ABC):
    name: str
    signature: inspect.Signature
    hints: dict[str, object]
    function: Callable[..., T]
    args_cleaner: Callable[[dict[str, object]], dict[str, object]]

    def check_args(self, args: dict[str, object] | None) -> None:
        try:
            if args is not None:
                _ = self.signature.bind(**self.args_cleaner(args))
            else:
                _ = self.signature.bind()
        except TypeError as e:
            raise FunctionParametersTypeError(func_name=self.name, exception=e) from e

    def is_function_return_type(self) -> bool:
        return self.hints["return"] == self.get_expected_type()

    @classmethod
    def factory(
        cls, name: str, signature: inspect.Signature, hints: dict[str, object], function: Callable[..., T]
    ) -> Self:
        if cls == BaseRegisteredFunction:
            raise TypeError("BaseRegisteredFunction cannot be instantiated directly. Use a subclass.")

        arg_c: Callable[[dict[str, object]], dict[str, object]] = lambda data: {
            k: v for k, v in data.items() if k in signature.parameters
        }

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


@dataclass(slots=True)
class RegisteredTransaction(BaseRegisteredFunction[str | None]):
    """Transaction output type is optional string"""

    def get_expected_type(self) -> UnionType | type[str]:
        return str | None


def _register[T](
    func: Callable[..., T],
    registry: dict[str, BaseRegisteredFunction[T]],
    register_type: type[BaseRegisteredFunction[T]],
):
    if func.__name__ in registry:
        raise ValueError(f"Function '{func.__name__}' is already registered")
    signature = inspect.signature(func)

    registered_function = register_type.factory(
        name=func.__name__,
        function=func,
        signature=signature,
        hints=get_type_hints(func, include_extras=True),
    )
    if not registered_function.is_function_return_type():
        raise ValueError(
            f"Function '{func.__name__}' has an invalid return type expected: {registered_function.get_expected_type().__name__} get : {registered_function.hints['return'].__name__}"
        )

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


def register_transaction(
    func: TFunc[str | None] | None = None,
    *,
    decorators: Sequence[TDecorator[str | None]] = (),
):
    return _reg(func, TRANSACTION_REGISTRY, RegisteredTransaction, decorators)


@dataclass(slots=True)
class RegisteredFunctionExecutor[T]:
    registered_function: BaseRegisteredFunction[T]
    parameters: dict[str, object] | None

    def execute(self, parameters_modified: Callable[[dict[str, object]], dict[str, object]] | None = None) -> T:
        params = self.parameters
        if self.parameters is not None and parameters_modified is not None:
            params = parameters_modified(self.parameters)
        if params is None:
            return self.registered_function.function()

        return self.registered_function.function(**self.registered_function.args_cleaner(params))

    @staticmethod
    def get_registered_function(
        data: dict[str, object], register_func: Callable[[str], BaseRegisteredFunction[T] | None]
    ) -> tuple[BaseRegisteredFunction[T], dict[str, object] | None]:
        function_name = data.get(FUNCTION_NAME_KEY)

        if not isinstance(function_name, str):
            raise TypeError(f"'{FUNCTION_NAME_KEY}' must be a 'string' found {type(function_name).__name__}")

        registered_function = register_func(function_name)
        if registered_function is None:
            raise ValueError(f"'{FUNCTION_NAME_KEY}' is not registered")

        parameters = data.get(FUNCTION_PARAMETERS_KEY, None)

        if parameters is not None and not isinstance(parameters, dict):
            raise TypeError(f"'{FUNCTION_PARAMETERS_KEY}' must be a 'dictionary' found {type(parameters).__name__}")

        registered_function.check_args(parameters)
        return registered_function, parameters


def _get_registered_executor[T](
    registry: dict[str, BaseRegisteredFunction[T]], name: str, parameters: dict[str, object] | None = None
) -> RegisteredFunctionExecutor[T] | None:
    registered_function = registry.get(name)
    if registered_function is None:
        return None
    return RegisteredFunctionExecutor(registered_function=registered_function, parameters=parameters)


def get_registered_function(
    function_name: str, parameters: dict[str, object] | None = None
) -> RegisteredFunctionExecutor[ActionNodeOutput] | None:
    return _get_registered_executor(FUNCTION_REGISTRY, function_name, parameters)


def get_registered_validator(
    validator_name: str, parameters: dict[str, object] | None = None
) -> RegisteredFunctionExecutor[bool] | None:
    return _get_registered_executor(VALIDATOR_REGISTRY, validator_name, parameters)


def get_registered_transaction(
    transaction_name: str, parameters: dict[str, object] | None = None
) -> RegisteredFunctionExecutor[str | None] | None:
    return _get_registered_executor(TRANSACTION_REGISTRY, transaction_name, parameters)


def get_and_check_registered[T](
    get_registered: Callable[[str, dict[str, object] | None], RegisteredFunctionExecutor[T] | None],
    data: dict[str, object],
    addition_parameters: dict[str, object] | None = None,
) -> RegisteredFunctionExecutor[T]:
    function_name = data.get(FUNCTION_NAME_KEY)
    if not isinstance(function_name, str):
        raise TypeError(f"expected '{FUNCTION_NAME_KEY}' type 'str' found: {type(function_name).__name__}")

    parameters = data.get(FUNCTION_PARAMETERS_KEY, None)
    if parameters is not None and not isinstance(parameters, dict):
        raise ValueError(f"expected '{FUNCTION_PARAMETERS_KEY}' type 'dict' found: {type(parameters).__name__}")

    if addition_parameters is not None:
        if parameters is None:
            parameters = addition_parameters
        else:
            parameters.update(addition_parameters)

    registered_function_ex = get_registered(function_name, parameters)
    if registered_function_ex is None:
        raise ValueError(f"'{FUNCTION_NAME_KEY}': {function_name} is not registered")

    registered_function_ex.registered_function.check_args(parameters)

    return registered_function_ex
