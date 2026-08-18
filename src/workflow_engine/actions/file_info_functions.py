import getpass
import hashlib
import mimetypes
import os
import platform
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import register_function
from workflow_engine.validators.functions_validators import file_exists_arg_validator


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="MD5 checksum of a file."
)
def md5_check_sum_file(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Calculate the MD5 checksum of a file."""
    with Path(file_path).open("rb") as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(65536)
            if not data:
                break
            m.update(data)
        return ActionNodeOutput(output_text=m.hexdigest())


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="File size bytes."
)
def file_size(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Get the size of a file in bytes."""
    size = Path(file_path).stat().st_size
    return ActionNodeOutput(output_text=str(size))


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="File last modification time"
)
def file_modify_time(file_path: Annotated[str, "Path to the file"], formater: Annotated[str, "Format for the date and time default: %Y-%m-%d %H:%M:%S"] = "%Y-%m-%d %H:%M:%S") -> ActionNodeOutput:
    """Get the last modification time of a file."""
    time = Path(file_path).stat().st_mtime
    return ActionNodeOutput(output_text=datetime.fromtimestamp(time, tz=UTC).strftime(formater))


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="File creation time"
)
def file_create_time(file_path: Annotated[str, "Path to the file"], formater: Annotated[str, "Format for the date and time default: %Y-%m-%d %H:%M:%S"] = "%Y-%m-%d %H:%M:%S") -> ActionNodeOutput:
    """Get the creation time of a file."""
    time = Path(file_path).stat().st_ctime
    return ActionNodeOutput(output_text=datetime.fromtimestamp(time, tz=UTC).strftime(formater))


UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="File size"
)
def file_size_human(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Get the size of a file in a human-readable format."""
    size = Path(file_path).stat().st_size

    unit = 0
    while size >= 1024 and unit < len(UNITS) - 1:
        size /= 1024
        unit += 1

    if unit == 0:
        return ActionNodeOutput(output_text=f"{int(size)} {UNITS[unit]}")

    return ActionNodeOutput(output_text=f"{size:.2f} {UNITS[unit]}")


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="MIME type of the file."
)
def file_mime_type(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Get the MIME type of file."""
    mime, _ = mimetypes.guess_type(file_path)
    return ActionNodeOutput(output_text=mime or "")


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="File encoding"
)
def file_encoding(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Get the encoding of a file. Tries several common encodings and returns the first one that successfully reads the file.
    If none of the encodings work, returns an empty string.
    utf-8/utf-8-sig/utf-16/cp1251/latin-1 are checked in order.
    """
    for enc in (
        "utf-8",
        "utf-8-sig",
        "utf-16",
        "cp1251",
        "latin-1",
    ):
        try:
            Path(file_path).read_text(encoding=enc)
            return ActionNodeOutput(output_text=enc)
        except UnicodeDecodeError:
            pass

    return ActionNodeOutput(output_text="")


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="Is a file executable"
)
def file_executable(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Check if a file is executable."""
    return ActionNodeOutput(output_text=str(os.access(file_path, os.X_OK)).lower())


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="File permissions"
)
def file_permissions(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Get the permissions of a file in symbolic notation (e.g., '-rwxr-xr-x')."""
    return ActionNodeOutput(output_text=stat.filemode(Path(file_path).stat().st_mode))


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="File owner"
)
def file_owner(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Get the owner of a file."""
    match platform.system():
        case "Linux" | "Darwin":
            # pwd is only available on Unix, so it is imported where it is used.
            from pwd import getpwuid

            return ActionNodeOutput(output_text=getpwuid(Path(file_path).stat().st_uid).pw_name)
        case "Windows":
            return ActionNodeOutput(output_text=getpass.getuser())
        case _:
            return ActionNodeOutput(output_text="N/A")


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="Is a file a symbolic link"
)
def is_symlink(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Check if a file is a symbolic link."""
    return ActionNodeOutput(output_text=str(Path(file_path).is_symlink()).lower())


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="Get the last access time of a file"
)
def access_time(
    file_path: Annotated[str, "Path to the file"],
    formater: Annotated[str, "Datetime format, default is '%Y-%m-%d %H:%M:%S'"] = "%Y-%m-%d %H:%M:%S",
) -> ActionNodeOutput:
    """Get the last access time of a file."""
    return ActionNodeOutput(output_text=datetime.fromtimestamp(Path(file_path).stat().st_atime, tz=UTC).strftime(formater))


@register_function(
    decorators=[file_exists_arg_validator({"file_path": 0})],
    summary="File SHA256 checksum"
)
def sha256_checksum_file(file_path: Annotated[str, "Path to the file"]) -> ActionNodeOutput:
    """Calculate the SHA256 checksum of a file."""
    h = hashlib.sha256()

    with Path(file_path).open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)

    return ActionNodeOutput(output_text=h.hexdigest())
