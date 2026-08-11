from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType

PARAM_TYPE_MISMATCH = "param_type_mismatch"
INVALID_WRITE_MODE = "invalid_write_mode"
INVALID_REMOVE_PARAM = "invalid_remove_param"
INVALID_COLLECTION_STATE = "invalid_collection_state"


class ModeType(Enum):
    PARAMETER = auto()
    MODIFY = auto()


class WriteParamMode(Enum):
    SET = auto()
    REPLACE = auto()
    APPEND = auto()
    EXTEND = auto()
    POP_LEFT = auto()
    DICT_UPDATE = auto()
    POP_RIGHT = auto()
    POP_INDEX = auto()
    REMOVE = auto()


def get_write_param_help(mode: WriteParamMode) -> str:
    match mode:
        case WriteParamMode.SET:
            return "Set a parameter"
        case WriteParamMode.REPLACE:
            return "Replace a parameter"
        case WriteParamMode.APPEND:
            return "Append to a parameter to list, set or deque"
        case WriteParamMode.EXTEND:
            return "Extend parameters to list, set or deque"
        case WriteParamMode.POP_LEFT:
            return "Pop deque from the left"
        case WriteParamMode.DICT_UPDATE:
            return "Update dictionary"
        case WriteParamMode.POP_RIGHT:
            return "Pop deque from the right"
        case WriteParamMode.POP_INDEX:
            return "Pop list or set by index"
        case WriteParamMode.REMOVE:
            return "Remove a parameter from list, set or deque"
        case _:
            return "Unknown mode"


def get_all_modes_help() -> str:
    return "\n".join(f"{mode.name}: {get_write_param_help(mode)}" for mode in WriteParamMode)


MODIFY_GROUP = (
    WriteParamMode.APPEND,
    WriteParamMode.EXTEND,
    WriteParamMode.DICT_UPDATE,
    WriteParamMode.POP_LEFT,
    WriteParamMode.POP_RIGHT,
    WriteParamMode.POP_INDEX,
    WriteParamMode.REMOVE,
)


@dataclass(frozen=True)
class ModifyResult:
    error_code: str | None
    error_msg: str | None
    collection: object


@dataclass(frozen=True)
class ModifyHandler[T]:
    object_type: type[T]
    copy_fn: Callable[[T], T]
    append_fn: dict[WriteParamMode, Callable[[T, object], None]]
    remove_fn: dict[WriteParamMode, Callable[[T, object], None]]
    check_fn: dict[WriteParamMode, list[Callable[[T, object], tuple[str, str] | None]]]
    allow_mode: tuple[WriteParamMode, ...]

    def update_collection(self, mode: WriteParamMode, m_object: object, value: object) -> ModifyResult:
        if not isinstance(m_object, self.object_type):
            return ModifyResult(
                PARAM_TYPE_MISMATCH,
                f"Expected collection of type {self.object_type.__name__}, got {type(m_object).__name__}",
                m_object,
            )
        if mode not in self.allow_mode:
            return ModifyResult(
                INVALID_WRITE_MODE,
                f"Invalid collection mode {mode} for collection type {self.object_type.__name__}",
                m_object,
            )
        if mode in self.check_fn:
            for checker in self.check_fn[mode]:
                result = checker(m_object, value)
                if result is not None:
                    return ModifyResult(*result, m_object)
        c_col = self.copy_fn(m_object)
        if mode in [WriteParamMode.APPEND, WriteParamMode.DICT_UPDATE, WriteParamMode.EXTEND]:
            self.append_fn[mode](c_col, value)
        else:
            self.remove_fn[mode](c_col, value)
        return ModifyResult(None, None, c_col)


_MODIFY_HANDLERS: MappingProxyType[type[object], ModifyHandler[object]]

_MODIFY_HANDLERS_MUT: dict[type[object], ModifyHandler[object]] = {}


def _register_collection[T](
    c_type: type[T],
    copy_fn: Callable[[T], T],
    append_fn: dict[WriteParamMode, Callable[[T, object], None]],
    remove_fn: dict[WriteParamMode, Callable[[T, object], None]],
    check_fn: dict[WriteParamMode, list[Callable[[T, object], tuple[str, str] | None]]],
    allow_mode: tuple[WriteParamMode, ...],
) -> None:
    _MODIFY_HANDLERS_MUT[c_type] = ModifyHandler[T](
        object_type=c_type,
        copy_fn=copy_fn,
        append_fn=append_fn,
        remove_fn=remove_fn,
        check_fn=check_fn,
        allow_mode=allow_mode,
    )


_register_collection(
    list,
    copy_fn=lambda x: list(x),
    append_fn={
        WriteParamMode.APPEND: lambda p_list, v: p_list.append(v),
        WriteParamMode.EXTEND: lambda p_list, v: p_list.extend(v) if isinstance(v, Iterable) else None,
    },
    remove_fn={
        WriteParamMode.POP_INDEX: lambda p_list, v: p_list.pop(v) if isinstance(v, int) else None,
        WriteParamMode.REMOVE: lambda p_list, v: p_list.remove(v),
    },
    check_fn={
        WriteParamMode.POP_INDEX: [
            lambda p_list, v: (
                (INVALID_COLLECTION_STATE, f"List is empty, cannot pop index {v.__repr__()}")
                if len(p_list) == 0
                else None
            ),
            lambda p_list, v: (
                (PARAM_TYPE_MISMATCH, f"Expected an integer - number for list index, got {type(v).__name__}")
                if not isinstance(v, int)
                else None
            ),
            lambda p_list, v: (
                (INVALID_COLLECTION_STATE, f"List index {v} is out of range for list of length {len(p_list)}")
                if isinstance(v, int) and (v < 0 or v >= len(p_list))
                else None
            ),
        ],
        WriteParamMode.REMOVE: [
            lambda p_list, v: (
                (INVALID_REMOVE_PARAM, f"value {v.__repr__()} not found in list") if v not in p_list else None
            )
        ],
        WriteParamMode.EXTEND: [
            lambda p_list, v: (
                (PARAM_TYPE_MISMATCH, f"Expected a Iterable for extend operation, got {type(v).__name__}")
                if not isinstance(v, Iterable)
                else None
            )
        ],
    },
    allow_mode=(WriteParamMode.APPEND, WriteParamMode.EXTEND, WriteParamMode.POP_INDEX, WriteParamMode.REMOVE),
)
_register_collection(
    deque,
    copy_fn=lambda p_deque: deque(p_deque),
    append_fn={
        WriteParamMode.APPEND: lambda p_deque, v: p_deque.append(v),
        WriteParamMode.EXTEND: lambda p_deque, v: p_deque.extend(v) if isinstance(v, Iterable) else None,
    },
    remove_fn={
        WriteParamMode.POP_LEFT: lambda p_deque, v: p_deque.popleft(),
        WriteParamMode.POP_RIGHT: lambda p_deque, v: p_deque.pop(),
        WriteParamMode.REMOVE: lambda p_deque, v: p_deque.remove(v),
    },
    check_fn={
        WriteParamMode.POP_LEFT: [
            lambda p_deque, v: (
                (INVALID_COLLECTION_STATE, "Deque is empty, cannot pop left") if len(p_deque) == 0 else None
            )
        ],
        WriteParamMode.POP_RIGHT: [
            lambda p_deque, v: (
                (INVALID_COLLECTION_STATE, "Deque is empty, cannot pop right") if len(p_deque) == 0 else None
            )
        ],
        WriteParamMode.REMOVE: [
            lambda p_deque, v: (
                (INVALID_REMOVE_PARAM, f"value {v.__repr__()} not found in deque") if v not in p_deque else None
            )
        ],
        WriteParamMode.EXTEND: [
            lambda p_deque, v: (
                (PARAM_TYPE_MISMATCH, f"Expected a Iterable for extend operation, got {type(v).__name__}")
                if not isinstance(v, Iterable)
                else None
            )
        ],
    },
    allow_mode=(
        WriteParamMode.APPEND,
        WriteParamMode.EXTEND,
        WriteParamMode.POP_LEFT,
        WriteParamMode.POP_RIGHT,
        WriteParamMode.REMOVE,
    ),
)
_register_collection(
    set,
    copy_fn=lambda p_set: set(p_set),
    append_fn={
        WriteParamMode.APPEND: lambda p_set, v: p_set.add(v),
        WriteParamMode.EXTEND: lambda p_set, v: type(p_set.update(v)) if isinstance(v, Iterable) else None,
    },
    remove_fn={WriteParamMode.REMOVE: lambda p_set, v: p_set.remove(v)},
    check_fn={
        WriteParamMode.REMOVE: [
            lambda p_set, v: (
                (INVALID_COLLECTION_STATE, "Set is empty, cannot remove element") if len(p_set) == 0 else None
            ),
            lambda p_set, v: (
                (INVALID_REMOVE_PARAM, f"Element {v.__repr__()} not found in set") if v not in p_set else None
            ),
        ],
        WriteParamMode.EXTEND: [
            lambda p_set, v: (
                (PARAM_TYPE_MISMATCH, f"Expected a Iterable for extend operation, got {type(v).__name__}")
                if not isinstance(v, Iterable)
                else None
            )
        ],
    },
    allow_mode=(WriteParamMode.APPEND, WriteParamMode.EXTEND, WriteParamMode.REMOVE),
)
_register_collection(
    dict,
    copy_fn=lambda p_dict: dict(p_dict),
    append_fn={WriteParamMode.DICT_UPDATE: lambda p_dict, v: p_dict.update(v) if isinstance(v, dict) else None},
    remove_fn={WriteParamMode.REMOVE: lambda p_dict, v: p_dict.pop(v, None)},
    check_fn={
        WriteParamMode.DICT_UPDATE: [
            lambda p_dict, v: (
                (PARAM_TYPE_MISMATCH, f"Expected a dictionary for update, got {type(v).__name__}")
                if not isinstance(v, dict)
                else None
            )
        ],
        WriteParamMode.REMOVE: [
            lambda p_dict, v: (
                (INVALID_REMOVE_PARAM, f"Key {v.__repr__()} not found in dictionary") if v not in p_dict else None
            )
        ],
    },
    allow_mode=(WriteParamMode.DICT_UPDATE, WriteParamMode.REMOVE),
)

_MODIFY_HANDLERS = MappingProxyType(_MODIFY_HANDLERS_MUT)
_MODIFY_HANDLERS_MUT = {}


def modify_param_object(m_object: object, param_name: str, mode: WriteParamMode, value: object) -> ModifyResult:
    if type(m_object) not in _MODIFY_HANDLERS:
        return ModifyResult(
            PARAM_TYPE_MISMATCH,
            f"Unsupported collection type {type(m_object).__name__} for parameter {param_name}",
            m_object,
        )
    handler = _MODIFY_HANDLERS[type(m_object)]
    return handler.update_collection(mode, m_object, value)
