from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from workflow_engine.exceptions import SessionBusyError, WorkflowConfigurationError

LOCK_FILE = "session.lock"


class SessionLock:
    """An exclusive hold on one session, taken around every call that writes its state.

    The engine is a single writer per session. Two processes running the same session would each
    read the state, act on it and write it back, and the second write would drop what the first one
    did, without either of them noticing. The hold is a file created with `O_CREAT | O_EXCL` in the
    session directory: creation either succeeds or reports that the file is there, in one step, on
    every platform the engine runs on. The holder's process id and the moment it took the lock are
    written into the file, so a refusal can say who is holding the session.

    A lock left behind by a process that died is not expired by age. A node waiting on a slow model
    call holds its session legitimately for minutes, and a lock taken away from a live run protects
    nothing. The refusal names the file instead, and removing it stays the operator's decision.

    The hold is re-entrant for the instance that owns it: a locked call reached from another locked
    call of the same engine counts down instead of deadlocking against itself.
    """

    session_id: str
    path: Path
    depth: int

    def __init__(self, session_id: str, session_dir: Path) -> None:
        self.session_id = session_id
        self.path = session_dir / LOCK_FILE
        self.depth = 0

    def _holder(self) -> str:
        """Describe the process that holds the file, from what it wrote when it took it."""

        try:
            record = json.loads(self.path.read_text(encoding="utf-8-sig"))
            return f"process {record['pid']} since {record['acquired_at']}"
        except (OSError, ValueError, KeyError, TypeError):
            return "another process"

    def acquire(self) -> None:
        if self.depth:
            self.depth += 1
            return
        record = json.dumps({"pid": os.getpid(), "acquired_at": datetime.now(tz=UTC).isoformat()}, sort_keys=True)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise SessionBusyError(self.session_id, self.path.as_posix(), self._holder()) from None
        except OSError as ex:
            raise WorkflowConfigurationError(
                f"Failed to lock the session at path: {self.path.resolve(strict=False)}"
            ) from ex
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as f:
                f.write(record)
        except OSError as ex:
            self.path.unlink(missing_ok=True)
            raise WorkflowConfigurationError(
                f"Failed to write the session lock at path: {self.path.resolve(strict=False)}"
            ) from ex
        self.depth = 1

    def release(self) -> None:
        if not self.depth:
            return
        self.depth -= 1
        if not self.depth:
            self.path.unlink(missing_ok=True)

    def __enter__(self) -> SessionLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()
