import datetime
from abc import ABC
from pathlib import Path

from workflow_engine.models.state import StateModel, StateSource
from workflow_engine.models.workflow import WorkflowModel, WorkflowSource


class Storage(StateSource,WorkflowSource,ABC):
    """Storage class for states and workflows."""
    def __init__(self, working_dir: Path):
        self.working_dir = working_dir

    def start_workflow(self, workflow_path: Path) -> tuple[StateModel, WorkflowModel]:
        workflow = self.upload_workflow(workflow_path)
        self.save_state(
            StateModel(
                timestamp=datetime.datetime.now(tz=datetime.UTC),
                work_dir=self.working_dir,
                schema_version=workflow.schema_version,
                flow_id=workflow.flow_id,
                current_node_id=workflow.start_node_id,
            )
        )

        return self.load_state(), workflow

    def continue_workflow(self) -> tuple[StateModel, WorkflowModel]:
        return self.load_state(), self.load_workflow()
