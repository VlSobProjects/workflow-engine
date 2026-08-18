from collections import deque
from pathlib import Path

from workflow_engine.registry.type_registry import Codec, IterableCodec, register_type


@register_type(
    set,
    summary="Persists set parameters.",
    description="Keeps a set state parameter a set across a save and a load. "
    "Items are converted recursively through their own codecs.",
)
class SetCodec(IterableCodec):
    @classmethod
    def list_to_collection(cls, value: list[object]) -> object:
        return set(value)


@register_type(
    deque,
    summary="Persists deque parameters.",
    description="Keeps a deque state parameter a deque across a save and a load. "
    "Items are converted recursively through their own codecs.",
)
class DequeCodec(IterableCodec):
    @classmethod
    def list_to_collection(cls, value: list[object]) -> object:
        return deque(value)


@register_type(
    list,
    summary="Persists list parameters.",
    description="Keeps a list state parameter a list across a save and a load. "
    "Items are converted recursively through their own codecs.",
)
class ListCodec(IterableCodec):
    @classmethod
    def list_to_collection(cls, value: list[object]) -> object:
        return value


@register_type(
    dict,
    summary="Persists dictionary parameters.",
    description="Keeps a dictionary state parameter a dictionary across a save and a load.",
)
class DictCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: dict) -> object:
        return dict(value)

    @classmethod
    def value_from_dict_obj(cls, value: object) -> dict:
        if not isinstance(value, dict):
            raise TypeError(f"Expected a dict, got {type(value).__name__}")
        return dict(value)


@register_type(
    str,
    summary="Persists string parameters.",
    description="Keeps a string state parameter a string across a save and a load.",
)
class StringCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: str) -> object:
        return value

    @classmethod
    def value_from_dict_obj(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Expected a string, got {type(value).__name__}")
        return value


@register_type(
    Path,
    summary="Persists filesystem path parameters.",
    description="Keeps a Path state parameter a Path across a save and a load. "
    "The value is stored in POSIX form, so it reads back identically from any shell.",
)
class PathCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: Path) -> object:
        return value.as_posix()

    @classmethod
    def value_from_dict_obj(cls, value: object) -> Path:
        if not isinstance(value, str):
            raise TypeError(f"Expected a string, got {type(value).__name__}")
        return Path(value)


@register_type(
    float,
    summary="Persists float parameters.",
    description="Keeps a float state parameter a float across a save and a load.",
)
class NumberCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: float) -> object:
        return value

    @classmethod
    def value_from_dict_obj(cls, value: object) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected a float, got {type(value).__name__}")
        return float(value)


@register_type(
    int,
    summary="Persists integer parameters.",
    description="Keeps an integer state parameter an integer across a save and a load.",
)
class IntCodec(Codec):
    @classmethod
    def value_to_dict_obj(cls, value: int) -> object:
        return value

    @classmethod
    def value_from_dict_obj(cls, value: object) -> int:
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected an int, got {type(value).__name__}")
        return int(value)
