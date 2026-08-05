from collections import deque
from pathlib import Path

from workflow_engine.registry.type_registry import Codec, IterableCodec, register_type


@register_type(set)
class SetCodec(IterableCodec):
    @classmethod
    def list_to_collection(cls, value: list[object]) -> object:
        return set(value)


@register_type(deque)
class DequeCodec(IterableCodec):
    @classmethod
    def list_to_collection(cls, value: list[object]) -> object:
        return deque(value)


@register_type(list)
class ListCodec(IterableCodec):
    @classmethod
    def list_to_collection(cls, value: list[object]) -> object:
        return value


@register_type(dict)
class DictCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: dict) -> object:
        return dict(value)

    @classmethod
    def value_from_dict_obj(cls, value: object) -> dict:
        if not isinstance(value, dict):
            raise TypeError(f"Expected a dict, got {type(value).__name__}")
        return dict(value)


@register_type(str)
class StringCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: str) -> object:
        return value

    @classmethod
    def value_from_dict_obj(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Expected a string, got {type(value).__name__}")
        return value


@register_type(Path)
class PathCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: Path) -> object:
        return value.as_posix()

    @classmethod
    def value_from_dict_obj(cls, value: object) -> Path:
        if not isinstance(value, str):
            raise TypeError(f"Expected a string, got {type(value).__name__}")
        return Path(value)


@register_type(float)
class NumberCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: float) -> object:
        return value

    @classmethod
    def value_from_dict_obj(cls, value: object) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected a float, got {type(value).__name__}")
        return float(value)


@register_type(int)
class IntCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: int) -> object:
        return value

    @classmethod
    def value_from_dict_obj(cls, value: object) -> int:
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected an int, got {type(value).__name__}")
        return int(value)
