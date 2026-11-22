from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from inspect import getmro
from typing import ClassVar

from workflow_engine.exceptions import WorkflowConfigurationError

CODECS: dict[type, type[Codec]] = {}
CODEC_REGISTRY: dict[str, type[Codec]] = {}


@dataclass(frozen=True)
class CodecMetadata:
    """Operator-facing description of a codec. See ADR 009."""

    summary: str
    description: str


CODEC_METADATA: dict[str, CodecMetadata] = {}

CODEC_OBJ = "object"
CODEC_OBJ_TYPE = "object_type"
CODEC_COLLECTION_ITEM = "item"
CODEC_COLLECTION_TYPE = "collection_type"


class Codec(ABC):
    _python_type: ClassVar[type]

    @classmethod
    @abstractmethod
    def value_to_dict_obj(cls, value: object) -> object:
        pass

    @classmethod
    def convert_to_dict(cls, value: object) -> object:
        return {CODEC_OBJ: cls.value_to_dict_obj(value), CODEC_OBJ_TYPE: cls.type_name()}

    @classmethod
    @abstractmethod
    def value_from_dict_obj(cls, value: object) -> object:
        pass

    @classmethod
    def python_type(cls) -> type:
        return cls._python_type

    @classmethod
    def type_name(cls) -> str:
        t = cls.python_type()
        return f"{t.__module__}.{t.__qualname__}"

    @classmethod
    def can_decode(cls, value: object) -> bool:
        return isinstance(value, cls.python_type())


class NoCodec(Codec):
    _python_type: ClassVar[type] = object

    @classmethod
    def convert_to_dict(cls, value: object) -> object:
        return value

    @classmethod
    def value_to_dict_obj(cls, value: object) -> object:
        return value

    @classmethod
    def value_from_dict_obj(cls, value: object) -> object:
        return value


def convert_from_dict(value_dict: object) -> tuple[object, type[Codec]]:
    """Decode a persisted ``{object, object_type}`` envelope, or return the value as it is.

    The stored name is resolved by the shared rule, so a full name another Python version wrote
    (``pathlib.Path`` on 3.14, ``pathlib._local.Path`` on 3.13) still finds its codec by the bare name.
    """
    if isinstance(value_dict, dict) and CODEC_OBJ in value_dict and CODEC_OBJ_TYPE in value_dict:
        value = value_dict[CODEC_OBJ]
        value_type = value_dict[CODEC_OBJ_TYPE]
        if isinstance(value_type, str):
            codec = find_codec_by_type_name(value_type)
            if codec is not None:
                return codec.value_from_dict_obj(value), codec
    return value_dict, NoCodec


def find_codec(value: object) -> type[Codec]:
    if value is None:
        return NoCodec
    mro = getmro(type(value))
    for value_type in mro:
        codec = CODECS.get(value_type)
        if codec is not None:
            return codec

    return NoCodec


def find_codec_by_type_name(type_name: str) -> type[Codec] | None:
    """Find a codec by a full registered name or an unambiguous bare class name, or None.

    An exact full name (``pathlib.Path``, ``builtins.int``) wins. Otherwise the bare class name
    (``Path``, ``int``) is matched against the live registry: exactly one match resolves and none
    means unknown. A full name that is not registered is reduced to its bare class name, since the
    module part changes with the interpreter (``pathlib.Path`` on 3.14, ``pathlib._local.Path`` on
    3.13) and a name another version wrote must still resolve. The bare index is built per call
    because plugins may register codecs after import.

    This is the one rule every surface that takes a codec name uses. An ambiguous bare name is raised
    rather than returned as a miss: several codecs answer to it, so calling it unknown would be wrong
    and picking one of them would be a guess. See ADR 012.
    """
    codec = CODEC_REGISTRY.get(type_name)
    if codec is not None:
        return codec
    bare_name = type_name.rsplit(".", 1)[-1]
    matches = {key: cls for key, cls in CODEC_REGISTRY.items() if key.rsplit(".", 1)[-1] == bare_name}
    if len(matches) == 1:
        return next(iter(matches.values()))
    if len(matches) == 0:
        return None
    raise WorkflowConfigurationError(
        f"Ambiguous codec type '{type_name}'; use the full name (one of: {', '.join(sorted(matches))})"
    )


def resolve_codec_by_type_name(type_name: str) -> type[Codec]:
    """Resolve a codec by the shared rule, refusing an unknown name. See ADR 012."""
    codec = find_codec_by_type_name(type_name)
    if codec is None:
        raise WorkflowConfigurationError(
            f"Unknown codec type '{type_name}'. Known types: {', '.join(sorted(CODEC_REGISTRY))}"
        )
    return codec


class IterableCodec(Codec, ABC):
    @classmethod
    def value_to_dict_obj(cls, values: object) -> object:
        if isinstance(values, Iterable):
            list_of_values = []
            cur_codec: type[Codec] = NoCodec
            item_type: type | None = None
            for item in values:
                if item_type is None or item_type is not type(item):
                    cur_codec = find_codec(item)
                    item_type = type(item)

                list_of_values.append(cur_codec.convert_to_dict(item))

            return list_of_values
        else:
            raise TypeError(f"Codec iterable_to_dict Expected an iterable, got {type(values).__name__}")

    @classmethod
    @abstractmethod
    def list_to_collection(cls, values: list[object]) -> object:
        pass

    @classmethod
    def value_from_dict_obj(cls, collection: object) -> object:
        if not isinstance(collection, list):
            raise TypeError(f"Codec iterable_from_dict Expected a list, got {collection.__class__.__name__}")
        objects: list[object] = [convert_from_dict(item)[0] for item in collection]
        return cls.list_to_collection(objects)


def register_type(codec_type: type, *, summary: str | None = None, description: str | None = None):
    def decorator(codec_cls: type[Codec]) -> type[Codec]:
        if not issubclass(codec_cls, Codec):
            raise TypeError(f"{codec_cls.__name__} is not a Codec")

        if codec_type in CODECS:
            registered = CODECS[codec_type]
            raise WorkflowConfigurationError(f"{codec_type.__name__!r} already registered by {registered.__name__}")

        codec_cls._python_type = codec_type

        CODECS[codec_type] = codec_cls
        CODEC_REGISTRY[codec_cls.type_name()] = codec_cls
        if summary is not None or description is not None:
            CODEC_METADATA[codec_cls.type_name()] = CodecMetadata(
                summary=summary or "", description=description or summary or ""
            )

        return codec_cls

    return decorator


def get_codec_metadata(type_name: str) -> CodecMetadata | None:
    return CODEC_METADATA.get(type_name)


def get_registered_codec_info() -> dict[str, str]:
    return {
        key: cls.python_type().__name__ if cls.python_type() is not None else "" for key, cls in CODEC_REGISTRY.items()
    }
