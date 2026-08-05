from abc import ABC

from workflow_engine.models.state import StateModel, StateSource
from workflow_engine.models.workflow import WorkflowModel, WorkflowSource


class Storage(StateSource, WorkflowSource, ABC):
    """Storage class for states and workflows."""

    def load_by_session(self, session_id: str) -> tuple[StateModel, WorkflowModel]:
        return self.load_state(session_id), self.load_workflow(session_id)

    def load_all_workflows(self) -> list[tuple[StateModel, WorkflowModel]]:
        return [(state, self.load_workflow(state.session_id)) for state in self.load_all_states()]
