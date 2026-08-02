import getpass
import hashlib
import mimetypes
import os
import platform
import stat
from datetime import UTC, datetime
from pathlib import Path
from pwd import getpwuid

from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import register_function
from workflow_engine.validators.functions_validators import file_exists_arg_validator


@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def md5_check_sum_file(file_path: str) -> ActionNodeOutput:
    with open(file_path, 'rb') as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(65536)
            if not data:
                break
            m.update(data)
        return ActionNodeOutput(
            output_text=m.hexdigest()
        )
def file_size(file_path:str)->ActionNodeOutput:
    size = Path(file_path).stat().st_size
    return ActionNodeOutput(output_text=str(size))

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_modify_time(file_path:str, formater:str = "%Y-%m-%d %H:%M:%S")->ActionNodeOutput:
    time = Path(file_path).stat().st_mtime
    return ActionNodeOutput(output_text=datetime.fromtimestamp(time,tz=UTC).strftime(formater))

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_create_time(file_path:str, formater:str = "%Y-%m-%d %H:%M:%S")->ActionNodeOutput:
    time = Path(file_path).stat().st_ctime
    return ActionNodeOutput(output_text=datetime.fromtimestamp(time,tz=UTC).strftime(formater))


UNITS = ("B", "KB", "MB", "GB", "TB", "PB")

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_size_human(file_path: Path) -> str:
    size = file_path.stat().st_size

    unit = 0
    while size >= 1024 and unit < len(UNITS) - 1:
        size /= 1024
        unit += 1

    if unit == 0:
        return f"{int(size)} {UNITS[unit]}"

    return f"{size:.2f} {UNITS[unit]}"

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_mime_type(file_path: Path) -> str:
    mime, _ = mimetypes.guess_type(file_path)
    return mime or ""

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_encoding(file_path: Path) -> str:
    for enc in (
        "utf-8",
        "utf-8-sig",
        "utf-16",
        "cp1251",
        "latin-1",
    ):
        try:
            file_path.read_text(encoding=enc)
            return enc
        except UnicodeDecodeError:
            pass

    return ""

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_executable(file_path: Path) -> str:
    return str(os.access(file_path, os.X_OK)).lower()

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_permissions(file_path: Path) -> str:
    return stat.filemode(file_path.stat().st_mode)

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def file_owner(file_path: Path) -> str:
    match platform.system():
        case "Linux" | "Darwin":
            return getpwuid(file_path.stat().st_uid).pw_name
        case "Windows":
            return getpass.getuser()
        case _:
            return "N/A"

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def is_symlink(file_path: Path) -> str:
    return str(file_path.is_symlink()).lower()

@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def access_time(
    file_path: Path,
    formater: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    return datetime.fromtimestamp(file_path.stat().st_atime, tz=UTC).strftime(formater)


@register_function(
    decorators=[
        file_exists_arg_validator({"file_path":0})
    ]
)
def sha256_checksum_file(file_path: Path) -> str:
    h = hashlib.sha256()

    with file_path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)

    return h.hexdigest()