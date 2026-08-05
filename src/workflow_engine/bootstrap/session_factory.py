from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.exceptions import WorkflowEngineError
from workflow_engine.models.state import StateModel
from workflow_engine.models.workflow import WorkflowModel

SESSION_DIRECTORY = "sessions"


class WorkflowSessionsFactory:
    work_dir: Path

    def __init__(self, config: WorkflowEngineConfiguration) -> None:
        self.work_dir = Path(config.work_dir)

    def get_all_sessions(self) -> list[str]:
        return [session.name for session in (self.work_dir / SESSION_DIRECTORY).iterdir() if session.is_dir()]

    def is_session(self, session_id: str) -> bool:
        return (self.work_dir / SESSION_DIRECTORY / session_id).is_dir()

    def new_session(self, workflow: WorkflowModel) -> StateModel:
        session_id = self._create_session_id()
        return StateModel(
            timestamp=datetime.now(tz=UTC),
            work_dir=self.work_dir / SESSION_DIRECTORY / session_id,
            schema_version=workflow.schema_version,
            flow_id=workflow.flow_id,
            current_node_id=workflow.start_node_id,
            session_id=session_id,
        )

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
            raise WorkflowEngineError(
                f"Failed to create a unique session ID work directory {e} session_dir: {session_dir}"
            ) from e

        if session_id is None:
            ex = WorkflowEngineError("Failed to create a unique session ID work directory after multiple attempts.")
            if last_error is not None:
                raise ex from last_error
            else:
                raise ex
        return session_id
