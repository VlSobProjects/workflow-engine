from __future__ import annotations

from dataclasses import dataclass, field


def decode_dict_none(obj: object) -> dict[str, object] | None:
    """Decode action parameters from a dictionary."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    else:
        raise TypeError(f"Expected a dictionary, got {type(obj).__name__}")

def decode_dict(obj: object) -> dict[str, object]:
    """Decode action parameters from a dictionary."""
    if isinstance(obj, dict):
        return obj
    else:
        raise TypeError(f"Expected a dictionary, got {type(obj).__name__}")

def decode_string_none(obj: object) -> str | None:
    """Decode action parameters from a string."""
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    else:
        raise TypeError(f"Expected a string, got {type(obj).__name__}")

def decode_list_of_dict_or_none(obj: object) -> list[dict[str, object]] | None:
    """Decode action parameters from a list of dictionaries."""
    if obj is None:
        return None
    if isinstance(obj, list) and all(isinstance(item, dict) for item in obj):
        return obj
    else:
        raise TypeError(f"Expected a list of dictionaries, got {type(obj).__name__}")

def decode_int_or_default(obj: object, def_val:int) -> int:
    """Decode action parameters from an integer."""
    if obj is None:
        return def_val
    if isinstance(obj, int):
        return obj
    else:
        raise TypeError(f"Expected an integer, got {type(obj).__name__}")

@dataclass(frozen=True)
class WorkflowNodeModel:
    id: str
    action_type: str
    action_parameters: dict[str, object]
    save_as: str | None = field(default=None)
    transition: list[dict[str, object]] | None = field(default=None)
    validator: list[dict[str, object]] | None = field(default=None)
    max_attempts: int = field(default=3)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowNodeModel:
        return cls(
            id=data['id'].__str__(),
            action_type=data['action_type'].__str__(),
            action_parameters=decode_dict(data['action_parameters']),
            save_as=decode_string_none(data.get('save_as')),
            transition=decode_list_of_dict_or_none(data.get('transition')),
            validator=decode_list_of_dict_or_none(data.get('validator')),
            max_attempts=decode_int_or_default(data.get('max_attempts'), 3)
        )
