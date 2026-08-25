from collections import deque
from collections.abc import Sized
from pathlib import Path
from typing import Annotated

from workflow_engine.collection_param_handlers import PARAM_TYPE_MISMATCH, WriteParamMode
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.function_registry import register_function
from workflow_engine.tools import render_value_as_text
from workflow_engine.validators.functions_validators import folder_exists_arg_validator, not_empty_str_arg_validator

FILE_NOT_FOUND = "file_not_found"
FILE_NOT_TEXT = "file_not_text"
FILE_READ_ERROR = "file_read_error"
INVALID_CHUNK_SIZE = "invalid_chunk_size"
SPLIT_NOT_TEXT = "split_not_text"
SPLIT_NO_TEXT = "split_no_text"


def set_items(
    param_writes: dict[str, ParamWrite],
    deque_name: str,
    items: list[object],
    set_mode: bool,
    cur_param_name_suffix: str | None = None,
    set_cur_param: bool = False,
    on_empty_items: str | None = None,
) -> None:
    if cur_param_name_suffix is not None and set_cur_param:
        cur_param = f"cur_{cur_param_name_suffix}"
        if len(items) > 0:
            param_writes[cur_param] = ParamWrite(mode=WriteParamMode.SET, value=items.pop(0), allow_overwrite=True)
        elif on_empty_items is not None:
            param_writes[cur_param] = ParamWrite(mode=WriteParamMode.SET, value=on_empty_items, allow_overwrite=True)

    if set_mode:
        param_writes[deque_name] = ParamWrite(mode=WriteParamMode.SET, value=deque(items))
    elif len(items) > 0:
        param_writes[deque_name] = ParamWrite(mode=WriteParamMode.EXTEND, value=items)


@register_function(
    decorators=[
        folder_exists_arg_validator({"path_target": 0}),
        not_empty_str_arg_validator({"folder_deque_name": 1, "file_deque_name": 2}),
    ],
    summary="Reads the paths in a folder into two deques",
)
def read_folder_items_to_deque(
    path_target: Annotated[str | Path, "Path to the target directory to scan"],
    folder_deque_name: Annotated[str, "Name of the state parameter that stores folder paths in a deque"],
    file_deque_name: Annotated[str, "Name of the state parameter that stores file paths in a deque"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to check whether deque parameters already exist"],
    on_empty_items: Annotated[str | None, "Value to return if the deque is empty default 'empty'"] = "empty",
) -> ActionNodeOutput:
    """Read directory paths and prepare state updates for files and folders.
    Set cur_file and cur_folder parameters - first item from list with allow_overwrite=True if lists is not empty.
    Set folder deque and file deque with the remaining items.
    """
    folder = Path(path_target)
    list_of_paths = [item.absolute() for item in folder.iterdir() if item.is_dir() or item.is_file()]
    param_writes: dict[str, ParamWrite] = {}
    list_of_files = [item for item in list_of_paths if item.is_file()]
    set_items(
        param_writes,
        file_deque_name,
        list_of_files,
        set_mode=state.get_param(file_deque_name) is None,
        cur_param_name_suffix="file",
        set_cur_param=True,
        on_empty_items=on_empty_items,
    )
    list_of_folders = [item for item in list_of_paths if item.is_dir()]
    set_items(
        param_writes,
        folder_deque_name,
        list_of_folders,
        set_mode=state.get_param(folder_deque_name) is None,
        cur_param_name_suffix="folder",
        set_cur_param=True,
        on_empty_items=on_empty_items,
    )
    return ActionNodeOutput(output_text=folder.absolute().as_posix(), param_writes=param_writes)


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 0})],
    summary="Initializes a deque parameter from a list of items.",
)
def init_deque_param(
    param_name: Annotated[str, "Name of the state parameter to create as a deque"],
    items: Annotated[list | None, "Initial items of the deque, front first; empty when omitted"] = None,
) -> ActionNodeOutput:
    """Create a deque parameter seeded with the given items.

    The main operator use is to prepare a work queue before a traversal loop: seed it with the
    starting items, extend it with functions such as 'enqueue_folder_entries', and consume it
    with 'set_param_from_deque'.
    """
    return ActionNodeOutput(
        output_text=param_name,
        param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=deque(items or []))},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 0})],
    summary="Initializes an empty list parameter.",
)
def init_list_param(
    param_name: Annotated[str, "Name of the state parameter to create as an empty list"],
    allow_overwrite: Annotated[
        bool, "Empty the parameter again when it already exists, for an accumulator inside a loop"
    ] = False,
) -> ActionNodeOutput:
    """Create an empty list parameter.

    The main operator use is to prepare an accumulator before a loop that appends to it, for
    example the 'functions' action with 'save_to_list' or 'dict_list_to_pretty_table'.

    A parameter that already exists is not overwritten unless 'allow_overwrite' says so: an
    accumulator that survives the loop it was made for is nearly always a mistake, and the write
    fails with 'param_overwrite_forbidden' instead. An inner loop that starts a fresh accumulation
    on every pass of an outer one - the parts of one file among many - is the case that asks for it.
    """
    return ActionNodeOutput(
        output_text=param_name,
        param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=[], allow_overwrite=allow_overwrite)},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"deque_param_name": 1})],
    summary="Extends a deque parameter with the entries of a folder.",
)
def enqueue_folder_entries(
    folder_path: Annotated[str | Path, "Path to the folder whose files and subfolders are enqueued"],
    deque_param_name: Annotated[str, "Name of the existing deque parameter to extend"],
) -> ActionNodeOutput:
    """Extend an existing deque parameter with the sorted entries of a folder.

    Files and subfolders are enqueued together as resolved POSIX paths, so repeated application
    combined with 'set_param_from_deque' walks a tree breadth-first. Returns the error code
    'folder_not_found' when the path is not a directory.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return ActionNodeOutput(
            output_text="",
            error_code="folder_not_found",
            error_msg=f"Folder '{folder_path}' does not exist",
        )

    entries = sorted(item.resolve().as_posix() for item in folder.iterdir() if item.is_dir() or item.is_file())
    if len(entries) > 0:
        return ActionNodeOutput(
            output_text=folder.resolve().as_posix(),
            param_writes={deque_param_name: ParamWrite(mode=WriteParamMode.EXTEND, value=entries)},
        )
    return ActionNodeOutput(output_text=folder.resolve().as_posix())


@register_function(summary="Pops an item from the front of a deque.")
def set_param_from_deque(
    deque_param_name: Annotated[str, "Name of the deque parameter to pop from"],
    param_name: Annotated[str, "Name of the parameter to set with the popped value"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to access the deque parameter"],
    on_empty: Annotated[str, "Value to return if the deque is empty default 'empty'"] = "empty",
    on_set: Annotated[
        str, "Value to return when a parameter is successfully set from the deque default 'popleft_from_deque'"
    ] = "popleft_from_deque",
    error_not_found: Annotated[
        str, "Error code to return if the deque parameter is not found default 'deque_not_found'"
    ] = "deque_not_found",
) -> ActionNodeOutput:
    """Pops an item from the front of a deque parameter and sets it to another parameter.
    If the deque is empty, sets the target parameter to a specified value.
    Returns an error if the deque parameter is not found."""
    deque_obj = state.get_param(deque_param_name, deque)
    if isinstance(deque_obj, deque):
        if len(deque_obj) == 0:
            return ActionNodeOutput(
                output_text=on_empty,
                param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=on_empty, allow_overwrite=True)},
            )
        else:
            value = deque_obj.popleft()
            param_writes = {
                deque_param_name: ParamWrite(mode=WriteParamMode.POP_LEFT, value=None),
                param_name: ParamWrite(mode=WriteParamMode.SET, value=value, allow_overwrite=True),
            }
            return ActionNodeOutput(output_text=on_set, param_writes=param_writes)
    return ActionNodeOutput(
        output_text="",
        error_code=error_not_found,
        error_msg=f"Deque parameter '{deque_param_name}' not found in state.",
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 0})],
    summary="Appends a value to an existing collection parameter.",
)
def append_to_param(
    param_name: Annotated[str, "Name of the existing list, deque or set parameter to append to"],
    value: Annotated[
        object,
        "Value to append; supports 'param.<name>', 'output.<node_id>' and 'artifact.<logical_name>' references",
    ],
    state: Annotated[StateReadOnlyView, "Read-only state view used to check that the parameter exists"],
    error_not_found: Annotated[
        str, "Error code to return if the parameter does not exist default 'param_not_found'"
    ] = "param_not_found",
) -> ActionNodeOutput:
    """Append one value to an existing list, deque or set parameter.

    The accumulating half of the collection family: 'init_list_param' prepares the parameter and this
    adds to it one value at a time, so a loop can collect what each pass produced — the answer to an
    interactive question, the output of the previous node — into one parameter a later node reads.

    A parameter that does not exist is the configured error code. A parameter holding something that
    cannot be appended to fails the write with 'param_type_mismatch'.
    """
    if state.get_param(param_name) is None:
        return ActionNodeOutput(
            output_text="",
            error_code=error_not_found,
            error_msg=f"Parameter '{param_name}' not found in state; create it with 'init_list_param' first.",
        )
    return ActionNodeOutput(
        output_text=param_name,
        param_writes={param_name: ParamWrite(mode=WriteParamMode.APPEND, value=value)},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 1})],
    summary="Reads the text of a file into a parameter.",
)
def read_text_file(
    file_path: Annotated[str | Path, "Path to the file to read"],
    param_name: Annotated[str, "Name of the parameter the text is written to"],
    encoding: Annotated[str, "Encoding the file is read with, 'utf-8' by default"] = "utf-8",
) -> ActionNodeOutput:
    """Read a file as text and put it on the bus under 'param_name'.

    This is how the content of a file reaches a step that works on text rather than on paths: the
    parameter is then inserted into a prompt, split into chunks or compared by a guard. Only the
    content travels; nothing about the file itself is read, which the file information functions do.

    The parameter is overwritten on every call, because a node that reads one file of many lives
    inside a loop by construction.

    A file that does not exist returns the error code 'file_not_found', a file that does not decode
    with the given encoding 'file_not_text', and any other read failure 'file_read_error'. All three
    are routable, so a scan can keep the file in its report instead of losing the run to it.
    """
    path = Path(file_path)
    if not path.is_file():
        return ActionNodeOutput(
            output_text="", error_code=FILE_NOT_FOUND, error_msg=f"File '{path.as_posix()}' does not exist"
        )
    try:
        text = path.read_text(encoding=encoding)
    except (UnicodeDecodeError, LookupError) as e:
        return ActionNodeOutput(
            output_text="",
            error_code=FILE_NOT_TEXT,
            error_msg=f"File '{path.as_posix()}' does not read as text in '{encoding}': {e}",
        )
    except OSError as e:
        return ActionNodeOutput(
            output_text="", error_code=FILE_READ_ERROR, error_msg=f"File '{path.as_posix()}' could not be read: {e}"
        )
    return ActionNodeOutput(
        output_text=param_name,
        param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=text, allow_overwrite=True)},
    )


def _text_chunks(text: str, chunk_size: int) -> list[str]:
    """Cut a text into pieces of at most 'chunk_size' characters, on a line boundary where there is one.

    The engine counts characters and never tokens: a tokenizer belongs to a model, and the core
    carries none (ADR 014 §5). So the size is a budget rather than a measurement, and the boundary
    is what makes the pieces usable - a paragraph, else a line, else the hard cut that guarantees
    progress on a text that carries neither.
    """
    chunks: list[str] = []
    start = 0
    while start < len(text):
        if start + chunk_size >= len(text):
            end = len(text)
        else:
            window = text[start : start + chunk_size]
            boundary = max(window.rfind("\n\n"), window.rfind("\n"))
            end = start + chunk_size if boundary <= 0 else start + boundary + 1
        piece = text[start:end]
        if piece.strip():
            chunks.append(piece)
        start = end
    return chunks


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 1})],
    summary="Splits a text into chunks in a deque.",
)
def split_text_to_deque(
    text: Annotated[str, "The text to split; a 'param.<name>' reference resolves to its value"],
    param_name: Annotated[str, "Name of the parameter the deque of chunks is written to"],
    chunk_size: Annotated[int, "Largest size of one chunk, in characters"],
) -> ActionNodeOutput:
    """Split a text into chunks and put them in a deque parameter, first chunk at the front.

    The preparing half of a chunked pass: this fills the queue, 'set_param_from_deque' consumes it
    one chunk per visit, and what each pass produced is accumulated with 'append_to_param'. The
    output text is the number of chunks, so a transition can route on how much work was made.

    The size is counted in characters and is a budget, not a measurement: the engine cannot count
    the tokens of a model, so a chunk that is still too large is answered by the provider and
    routed by the node that made the call. A chunk ends on the last paragraph or line break that
    fits, and on the budget itself where the text carries neither. Chunks holding nothing but
    whitespace are dropped rather than sent to a model.

    The parameter is overwritten on every call, because a node that splits one text of many lives
    inside a loop by construction. A 'chunk_size' below one returns the error code
    'invalid_chunk_size', a value that is not text 'split_not_text', and a text with nothing in it
    'split_no_text'.
    """
    if not isinstance(text, str):
        return ActionNodeOutput(
            output_text="", error_code=SPLIT_NOT_TEXT, error_msg=f"'text' must be a string, got {type(text).__name__}."
        )
    if chunk_size < 1:
        return ActionNodeOutput(
            output_text="",
            error_code=INVALID_CHUNK_SIZE,
            error_msg=f"'chunk_size' must be at least 1 character, got {chunk_size}.",
        )
    chunks = _text_chunks(text, chunk_size)
    if len(chunks) == 0:
        return ActionNodeOutput(
            output_text="", error_code=SPLIT_NO_TEXT, error_msg="The text carries nothing that could be split."
        )
    return ActionNodeOutput(
        output_text=str(len(chunks)),
        param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value=deque(chunks), allow_overwrite=True)},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 0})],
    summary="Initializes an empty dictionary parameter.",
)
def init_dict_param(
    param_name: Annotated[str, "Name of the state parameter to create as an empty dictionary"],
    allow_overwrite: Annotated[
        bool, "Empty the parameter again when it already exists, for a fresh assembly inside a loop"
    ] = False,
) -> ActionNodeOutput:
    """Create an empty dictionary parameter.

    The dictionary half of the collection family: prepare the parameter before the loop that fills
    it, with 'set_dict_item' writing one key per pass or 'append_to_dict_key' grouping values under
    one. What the loop assembles is a document a later node reads whole - a plan, findings by
    subsystem, files by content hash.

    A parameter that already exists is not overwritten unless 'allow_overwrite' says so, and the
    write fails with 'param_overwrite_forbidden' instead, for the same reason 'init_list_param'
    refuses: an assembly that survives the loop it was made for is nearly always a mistake.
    """
    return ActionNodeOutput(
        output_text=param_name,
        param_writes={param_name: ParamWrite(mode=WriteParamMode.SET, value={}, allow_overwrite=allow_overwrite)},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"dict_param_name": 0})],
    summary="Sets one key of an existing dictionary parameter.",
)
def set_dict_item(
    dict_param_name: Annotated[str, "Name of the existing dictionary parameter to write into"],
    key: Annotated[
        object,
        "Key to set; a 'param.'/'output.' reference resolves first, and the key is rendered as text "
        "by the one rule, so a path keys in POSIX form",
    ],
    value: Annotated[
        object,
        "Value to store under the key; supports 'param.<name>', 'output.<node_id>' and "
        "'artifact.<logical_name>' references",
    ],
    state: Annotated[StateReadOnlyView, "Read-only state view used to check that the parameter exists"],
    error_not_found: Annotated[
        str, "Error code to return if the parameter does not exist default 'param_not_found'"
    ] = "param_not_found",
) -> ActionNodeOutput:
    """Set one key of an existing dictionary parameter.

    The setting half of the dictionary family: 'init_dict_param' prepares the parameter and this
    writes one key at a time, so a loop can key what each pass produced - the category a model
    answered, keyed by the file it was asked about. The key is rendered as text by the one rule
    (ADR 008), because a state dictionary round-trips through JSON and its keys are text.

    The write is a DICT_UPDATE of the touched key alone, so the run shows what the node changed
    rather than the whole dictionary. A parameter that does not exist is the configured error code;
    one that is not a dictionary is 'param_type_mismatch'.
    """
    current = state.get_param(dict_param_name)
    if current is None:
        return ActionNodeOutput(
            output_text="",
            error_code=error_not_found,
            error_msg=f"Parameter '{dict_param_name}' not found in state; create it with 'init_dict_param' first.",
        )
    if not isinstance(current, dict):
        return ActionNodeOutput(
            output_text="",
            error_code=PARAM_TYPE_MISMATCH,
            error_msg=f"Parameter '{dict_param_name}' holds {type(current).__name__}, not a dictionary.",
        )
    key_text = render_value_as_text(key)
    return ActionNodeOutput(
        output_text=key_text,
        param_writes={dict_param_name: ParamWrite(mode=WriteParamMode.DICT_UPDATE, value={key_text: value})},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"dict_param_name": 0})],
    summary="Appends a value to a list kept under one key of a dictionary parameter.",
)
def append_to_dict_key(
    dict_param_name: Annotated[str, "Name of the existing dictionary parameter that groups the values"],
    key: Annotated[
        object,
        "Key to group under; a 'param.'/'output.' reference resolves first, and the key is rendered "
        "as text by the one rule",
    ],
    value: Annotated[
        object,
        "Value to append under the key; supports 'param.<name>', 'output.<node_id>' and "
        "'artifact.<logical_name>' references",
    ],
    state: Annotated[StateReadOnlyView, "Read-only state view used to read the current group of the key"],
    error_not_found: Annotated[
        str, "Error code to return if the parameter does not exist default 'param_not_found'"
    ] = "param_not_found",
) -> ActionNodeOutput:
    """Append one value to the list kept under one key of a dictionary parameter.

    The grouping half of the dictionary family: where 'set_dict_item' keeps one value per key, this
    collects every value a key receives - files grouped by their content hash, findings grouped by
    the subsystem they implicate. A key seen for the first time starts its list with this value.

    The write is a DICT_UPDATE carrying the touched key with its extended list, so the run shows
    which group grew. A parameter that does not exist is the configured error code; one that is not
    a dictionary, or a key already holding something that is not a list, is 'param_type_mismatch'.
    """
    current = state.get_param(dict_param_name)
    if current is None:
        return ActionNodeOutput(
            output_text="",
            error_code=error_not_found,
            error_msg=f"Parameter '{dict_param_name}' not found in state; create it with 'init_dict_param' first.",
        )
    if not isinstance(current, dict):
        return ActionNodeOutput(
            output_text="",
            error_code=PARAM_TYPE_MISMATCH,
            error_msg=f"Parameter '{dict_param_name}' holds {type(current).__name__}, not a dictionary.",
        )
    key_text = render_value_as_text(key)
    existing = current.get(key_text)
    if existing is None:
        items: list[object] = [value]
    elif isinstance(existing, list):
        items = [*existing, value]
    else:
        return ActionNodeOutput(
            output_text="",
            error_code=PARAM_TYPE_MISMATCH,
            error_msg=(
                f"Key '{key_text}' of '{dict_param_name}' holds {type(existing).__name__}, which cannot be appended to."
            ),
        )
    return ActionNodeOutput(
        output_text=key_text,
        param_writes={dict_param_name: ParamWrite(mode=WriteParamMode.DICT_UPDATE, value={key_text: items})},
    )


@register_function(
    decorators=[not_empty_str_arg_validator({"dict_param_name": 0, "target_param_name": 1})],
    summary="Keeps the entries of a dictionary parameter whose values are large enough.",
)
def filter_dict_by_value_size(
    dict_param_name: Annotated[str, "Name of the existing dictionary parameter to filter"],
    target_param_name: Annotated[str, "Name of the parameter the kept entries are written to"],
    minimum: Annotated[int, "Smallest value size that is kept; supports 'param.<name>' references"],
    state: Annotated[StateReadOnlyView, "Read-only state view used to read the dictionary"],
    allow_overwrite: Annotated[
        bool, "Overwrite the target parameter when it already exists, for a filter inside a loop"
    ] = False,
    error_not_found: Annotated[
        str, "Error code to return if the parameter does not exist default 'param_not_found'"
    ] = "param_not_found",
) -> ActionNodeOutput:
    """Keep the entries of a dictionary whose values hold at least 'minimum' items.

    The reading half of a grouping loop: 'append_to_dict_key' collects values under their keys, and
    this extracts the groups that matter - the hashes more than one file shares are exactly the
    duplicates, the subsystems with more than one finding are where the evidence points. The check
    is code, so what the groups mean is decided before any model reads them.

    The kept entries land in the target parameter as a dictionary of their own; the source is not
    changed. The output text is the number of kept entries, so a transition can route on whether
    anything qualified. A value that has no size cannot meet the bound and is dropped. A source
    that does not exist is the configured error code; one that is not a dictionary is
    'param_type_mismatch'.
    """
    current = state.get_param(dict_param_name)
    if current is None:
        return ActionNodeOutput(
            output_text="",
            error_code=error_not_found,
            error_msg=f"Parameter '{dict_param_name}' not found in state; create it with 'init_dict_param' first.",
        )
    if not isinstance(current, dict):
        return ActionNodeOutput(
            output_text="",
            error_code=PARAM_TYPE_MISMATCH,
            error_msg=f"Parameter '{dict_param_name}' holds {type(current).__name__}, not a dictionary.",
        )
    kept = {key: value for key, value in current.items() if isinstance(value, Sized) and len(value) >= minimum}
    return ActionNodeOutput(
        output_text=str(len(kept)),
        param_writes={
            target_param_name: ParamWrite(mode=WriteParamMode.SET, value=kept, allow_overwrite=allow_overwrite)
        },
    )
