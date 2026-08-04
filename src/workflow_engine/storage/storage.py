from abc import ABC

from workflow_engine.models.state import StateModel, StateSource
from workflow_engine.models.workflow import WorkflowModel, WorkflowSource


class Storage(StateSource, WorkflowSource, ABC):
    """Storage class for states and workflows."""

    def __init__(self, session_id: str):
        self.session_id = session_id

    def continue_workflow(self) -> tuple[StateModel, WorkflowModel]:
        return self.load_state(), self.load_workflow()
