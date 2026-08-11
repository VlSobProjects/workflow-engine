from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4

from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.exceptions import WorkflowConfigurationError, WorkflowRuntimeError
from workflow_engine.models.state import StateModel
from workflow_engine.models.workflow import WorkflowModel
from workflow_engine.tools import parameter_from_dict

SESSION_DIRECTORY = "sessions"
SESSION_FILE = "session.json"


@dataclass
class WorkflowSession:
    timestamp: datetime
    session_id: str
    work_dir: Path
    flow_id: str
    schema_version: str
    storage: MappingProxyType[str, str]

    def create_state(self, workflow: WorkflowModel) -> StateModel:
        return StateModel(
            timestamp=datetime.now(tz=UTC),
            work_dir=self.work_dir,
            schema_version=workflow.schema_version,
            flow_id=workflow.flow_id,
            current_node_id=workflow.start_node_id,
            session_id=self.session_id,
        )

    def is_same(self, state: StateModel) -> bool:
        return (
            self.session_id == state.session_id
            and self.work_dir == state.work_dir
            and self.flow_id == state.flow_id
            and self.schema_version == state.schema_version
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "work_dir": self.work_dir.as_posix(),
            "flow_id": self.flow_id,
            "schema_version": self.schema_version,
            "storage": dict(self.storage),
        }

    @classmethod
    def from_dict(cls, session: dict[str, object]) -> WorkflowSession:
        return WorkflowSession(
            timestamp=datetime.fromisoformat(parameter_from_dict(session, "timestamp", str)),
            session_id=parameter_from_dict(session, "session_id", str),
            work_dir=Path(parameter_from_dict(session, "work_dir", str)),
            flow_id=parameter_from_dict(session, "flow_id", str),
            schema_version=parameter_from_dict(session, "schema_version", str),
            storage=MappingProxyType(parameter_from_dict(session, "storage", dict)),
        )


class WorkflowSessionsFactory:
    work_dir: Path

    def __init__(self, config: WorkflowEngineConfiguration) -> None:
        self.work_dir = Path(config.work_dir)

    @staticmethod
    def _ensure_directory(path_value: str | Path, context: str) -> Path:
        path = Path(path_value).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as ex:
            raise WorkflowConfigurationError(
                f"Failed to create {context} directory: {path.resolve(strict=False)}"
            ) from ex
        return path.resolve(strict=False)

    def get_all_sessions(self) -> list[str]:
        if not (self.work_dir / SESSION_DIRECTORY).exists():
            return []
        return [session.name for session in (self.work_dir / SESSION_DIRECTORY).iterdir() if session.is_dir()]

    def is_session(self, session_id: str) -> bool:
        return (self.work_dir / SESSION_DIRECTORY / session_id).is_dir()

    @classmethod
    def check_session(cls, session: WorkflowSession, session_path: Path, session_id: str):
        if session_path.parent.absolute() != session.work_dir.absolute():
            raise WorkflowRuntimeError(
                f"Session path {session_path} is not in the expected work directory {session.work_dir}"
            )
        if session_id != session.session_id:
            raise WorkflowRuntimeError(
                f"Session path {session_path} does not match the expected session ID {session.session_id}"
            )

    def load_session(self, session_id: str) -> WorkflowSession:
        session_path = self.work_dir / SESSION_DIRECTORY / session_id / SESSION_FILE
        if not session_path.exists():
            raise WorkflowRuntimeError(f"Session file not found at path: {session_path.absolute()}")
        try:
            with session_path.open() as f:
                json_obj = json.load(f)
            session = WorkflowSession.from_dict(json_obj)
        except JSONDecodeError as e:
            raise WorkflowRuntimeError(
                f"session Json corrupted - Failed to load session: {session_id} from file: {session_path}"
            ) from e
        except OSError as e:
            raise WorkflowRuntimeError(f"Failed to load session: {session_id} from file: {session_path}") from e

        self.check_session(session, session_path, session_id)
        return session

    def new_session(self, workflow: WorkflowModel, storage_config: MappingProxyType[str, str]) -> WorkflowSession:
        session_id = self._create_session_id()
        session_dir = self.work_dir / SESSION_DIRECTORY / session_id
        session_path = session_dir / SESSION_FILE
        storage_dir = parameter_from_dict(storage_config, "storage_dir", str)
        try:
            self._ensure_directory(session_dir, "session")
            self._ensure_directory(storage_dir, "storage")
            session = WorkflowSession(
                timestamp=datetime.now(tz=UTC),
                session_id=session_id,
                work_dir=session_dir.resolve(strict=False),
                flow_id=workflow.flow_id,
                schema_version=workflow.schema_version,
                storage=storage_config,
            )
            with session_path.open(mode="w") as session_file:
                json.dump(session.to_dict(), session_file)
        except OSError as e:
            raise WorkflowRuntimeError(f"Failed to create session file: {session_path}") from e

        return session

    def _create_session_id(self) -> str:
        """Create a new unique session ID."""
        session_id = None
        attempts = 0
        last_error = None
        session_dir = None
        try:
            while session_id is None and attempts < 3:
                uuid = str(uuid4())
                session_dir: Path = self.work_dir / SESSION_DIRECTORY / uuid
                try:
                    session_dir.mkdir(parents=True, exist_ok=False)
                    session_id = uuid
                except FileExistsError as e:
                    attempts += 1
                    last_error = e
        except OSError as e:
            raise WorkflowRuntimeError(
                f"Failed to create a unique session ID work directory {e} session_dir: {session_dir}"
            ) from e

        if session_id is None:
            ex = WorkflowRuntimeError("Failed to create a unique session ID work directory after multiple attempts.")
            if last_error is not None:
                raise ex from last_error
            else:
                raise ex
        return session_id
