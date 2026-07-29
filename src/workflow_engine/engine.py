from workflow_engine.actions.base_actions import ExecutionMode, BaseAutomaticAction
from workflow_engine.models.state import StateModel
from workflow_engine.models.workflow import WorkflowModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.storage.storage import Storage
from workflow_engine.validators.output_validators import BaseOutputValidator
from workflow_engine.workflow import WorkflowNode, workflow_node_factory

WORKFLOW_NODES : dict[str,WorkflowNode] = {}


def get_workflow_node(node_id: str) -> WorkflowNode | None:
    return WORKFLOW_NODES.get(node_id)

def is_workflow_node(node_id: str) -> bool:
    return node_id in WORKFLOW_NODES

def add_dynamic_workflow_node(node: WorkflowNode)->str:
    node_id = _get_unique_id_for_node(node)
    node.id = node_id
    WORKFLOW_NODES[node_id] = node
    return node_id

def _get_unique_id_for_node(node: WorkflowNode) ->str:
    if node.id not in WORKFLOW_NODES:
        return node.id
    node_id_suffix = 1
    while node.id+"_"+str(node_id_suffix) in WORKFLOW_NODES:
        node_id_suffix += 1
    return node.id+"_"+str(node_id_suffix)

def _load_workflow_nodes(workflow: WorkflowModel):
     global WORKFLOW_NODES
     WORKFLOW_NODES = {node.id: workflow_node_factory(node) for node in workflow.nodes}

def validate_output(output:ActionNodeOutput,validators:list[BaseOutputValidator], state:StateModel)->bool:
    for validator in validators:
        validator.validate_output()


def sart_engine(storage: Storage):
    state, workflow = storage.continue_workflow()
    _load_workflow_nodes(workflow)
    def load_state():
        nonlocal state
        state = storage.load_state()

    while True:
        node = get_workflow_node(state.current_node_id)
        if node is None:
            print(f"Engine stop: Node with id {state.current_node_id} not found in workflow")
            break
         
        if isinstance(node.action, BaseAutomaticAction):

            output = node.action.execute(state)

                
        load_state()



