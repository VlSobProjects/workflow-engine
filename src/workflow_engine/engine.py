from workflow_engine.actions.action_present import PresentResponse
from workflow_engine.actions.base_actions import (
    BaseAutomaticAction,
    BaseInteractiveAction,
)
from workflow_engine.exceptions import WorkflowError
from workflow_engine.models.state import StateModel
from workflow_engine.models.workflow import WorkflowModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.storage.storage import Storage
from workflow_engine.transition.base import BaseTransaction, WithErrors
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

def _workflow_nodes_errors(workflow: dict[str, WorkflowNode]) ->dict[str,str]:
    errors = {}
    for node in workflow.values():
        error_count = 1
        try:
            if node.transitions is not None:
                for transition in node.transitions:
                    transition.check_error(set(workflow.keys()))
        except WorkflowError as e:
            errors[node.id] = f"Error {error_count} in node {node.id}: {e.__str__()}"
            error_count += 1
    
    return errors
    

def _validate_output(output:ActionNodeOutput, validators:list[BaseOutputValidator], state:StateModel)->bool:
    for validator in validators:
        if not validator._validate_output(output.output_text, state):
            return False
    return True

def _next_on_error(cur_node: WorkflowNode,nex_node: WorkflowNode,output:ActionNodeOutput,allow_attempts:bool ,attempts: int) -> WorkflowNode:
    if allow_attempts and cur_node.config.max_attempts > attempts:
        print(f"Attempt on error: {attempts + 1} node id: {cur_node.id} max attempts: {cur_node.config.max_attempts}, {output.on_error()}")
        return cur_node
    else:
        print(f"Transition on error to {nex_node.id}, {output.on_error()}")
        return nex_node

def _retry_node(output:ActionNodeOutput, cur_node: WorkflowNode,attempts:int)-> WorkflowNode | None:
    if cur_node.config.max_attempts > attempts:
        print(f"Attempt on error: {attempts + 1} node id: {cur_node.id} max attempts: {cur_node.config.max_attempts}, {output.on_error()}")
        return cur_node

    print(f"No transition on error for node, attempt: {attempts}, max attempts: {cur_node.config.max_attempts}, node id: {cur_node.id}, {output.on_error()}")
    return None


def _transition_on_error(transition:list[BaseTransaction] | None, cur_node: WorkflowNode, output:ActionNodeOutput, state:StateModel, workflow_nodes: dict[str, WorkflowNode])-> WorkflowNode | None:
    attempts = state.attempt_counters.get(cur_node.id, 0)
    if transition is not None:
        for tr in [t for t in transition if t.is_on_error()]:
            next_node_id = tr.transition(output, state, set(workflow_nodes.keys()))
            if next_node_id and next_node_id in workflow_nodes:
                return _next_on_error(cur_node,workflow_nodes[next_node_id],output,isinstance(tr,WithErrors) and tr.attempts,attempts)
        
    return _retry_node(output, cur_node, attempts)

def _proceed_with_output(output: ActionNodeOutput | None, cur_node: WorkflowNode, state: StateModel, workflow_nodes: dict[str, WorkflowNode]) -> WorkflowNode | None:
    if output:
        if output.error_code:
            return _transition_on_error(cur_node.transitions, cur_node, output, state, workflow_nodes)
        else:
            if not _validate_output(output, cur_node.validators if cur_node.validators else [], state):
                print(f"Validation failed for node {cur_node.id}")
                output.error_code = "validation_failed"
                output.error_message = f"Validation failed for node {cur_node.id}"
                return _transition_on_error(cur_node.transitions, cur_node, output, state, workflow_nodes)
            else:
                print(f"Node {cur_node.id} executed successfully, output: {output.output_text}")
                if cur_node.transitions is not None:
                    for tr in [t for t in cur_node.transitions if not t.is_on_error()]:
                        next_node_id = tr.transition(output, state, set(workflow_nodes.keys()))
                        if next_node_id and next_node_id in workflow_nodes:
                            print(f"Transitioning to node {next_node_id} from node {cur_node.id}")
                            return workflow_nodes[next_node_id]

                print(f"No transition found for node {cur_node.id}, workflow will stop.")
                return None
    else:
        return cur_node


def sart_engine(storage: Storage, output: ActionNodeOutput | None) -> PresentResponse:
    state, workflow = storage.continue_workflow()
    _load_workflow_nodes(workflow)
    # def load_state():
    #     nonlocal state
    #     state = storage.load_state()

    cur_node = get_workflow_node(state.current_node_id)
    if cur_node is None:
        print(
            f"Engine stop: Node with id {state.current_node_id} not found in workflow"
        )
        return PresentResponse(
            title="Error in workflow setup",
            description="Current node not found in workflow by id",
            instruction="Probably workflow session is corrupted. Please check workflow configuration, and try start new session",
            hints=["Current Workflow Sate:", f"working folder: {state.work_dir}"]
            + state.info()
            + state.info_errors()
            + state.info_params()
            + state.info_outputs(),
            errors={
                f"Current node id: {state.current_node_id}": "not found in workflow"
            },
        )

    errors = _workflow_nodes_errors(WORKFLOW_NODES)
    if len(errors) > 0:
        return PresentResponse(
            title="Error in workflow setup",
            description="Workflow nodes is not pass validation.",
            instruction="Please check workflow configuration. In errors - all configuration errors",
            hints=["Current Workflow Sate:", f"working folder: {state.work_dir}"]
            + state.info()
            + state.info_errors()
            + state.info_params()
            + state.info_outputs(),
            errors=errors,
            goal="Fix workflow configuration using information from Errors. Re run workflow or start new with fixed version of workflow configuration.",
        )
    

    try:
        while cur_node is not None:
            next_node = _proceed_with_output(output, cur_node, state, WORKFLOW_NODES)
            state.update(cur_node.id,cur_node.config.save_as, output, next_node.id if next_node else None)
            storage.save_state(state)
            cur_node = next_node

            if cur_node and isinstance(cur_node.action, BaseAutomaticAction):
                output = cur_node.action.execute(state)
            elif cur_node and isinstance(cur_node.action, BaseInteractiveAction):
                return cur_node.action.present(state)



    except Exception as e:
        print(f"Engine stop: Exception occurred during workflow execution: {e}")
        return PresentResponse(
            title="Error in workflow execution",
            description="An exception occurred during workflow execution.",
            instruction="Please check Exception in Errors and state,",
            hints=["Current Workflow Sate:", f"working folder: {state.work_dir}"]
            + state.info()
            + state.info_errors()
            + state.info_params()
            + state.info_outputs(),
            errors={f"Exception: {type(e).__name__}": str(e)},
        )

    storage.save_state(state)

    return PresentResponse(
            title="Loop finished",
            description="All nodes have been processed, and the workflow has completed.",
            instruction="Workflow execution completed successfully. Check state.",
            hints=["Current Workflow Sate:", f"working folder: {state.work_dir}"]
            + state.info()
            + state.info_errors()
            + state.info_params()
            + state.info_outputs(),
        )



