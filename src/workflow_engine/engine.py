from workflow_engine.workflow import WorkflowNode

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
