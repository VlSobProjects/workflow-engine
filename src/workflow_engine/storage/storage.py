from abc import ABC

from workflow_engine.models.node_record import RecordSource
from workflow_engine.models.state import StateModel, StateSource
from workflow_engine.models.workflow import WorkflowModel, WorkflowSource


class Storage(StateSource, WorkflowSource, RecordSource, ABC):
    """Storage class for states, workflows and node records."""

    def load_by_session(self, session_id: str) -> tuple[StateModel, WorkflowModel]:
        return self.load_state(session_id), self.load_workflow(session_id)
