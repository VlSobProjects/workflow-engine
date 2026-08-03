from dataclasses import dataclass

from workflow_engine.actions.action_present import PresentResponse
from workflow_engine.actions.base_actions import (
    BaseAutomaticAction,
    BaseInteractiveAction,
)
from workflow_engine.exceptions import WorkflowEngineError, WorkflowParameterError, WorkflowRuntimeError
from workflow_engine.models.state import GuardRecord, StateModel
from workflow_engine.models.workflow import WorkflowModel
from workflow_engine.output import ActionNodeOutput
from workflow_engine.storage.storage import Storage
from workflow_engine.transition.base import EndTarget, FailTarget, NodeTarget, Transition
from workflow_engine.workflow import WorkflowNode, workflow_node_factory

WORKFLOW_NODES: dict[str, WorkflowNode] = {}

NO_TRANSITION_ERROR = "no_transition_matched"
ATTEMPTS_EXCEEDED_ERROR = "max_attempts_exceeded"


@dataclass(frozen=True, slots=True)
class Step:
    """What the engine does after a node: continue, end, or fail."""

    next_node: WorkflowNode | None = None
    failure: str | None = None


def get_workflow_node(node_id: str) -> WorkflowNode | None:
    return WORKFLOW_NODES.get(node_id)


def is_workflow_node(node_id: str) -> bool:
    return node_id in WORKFLOW_NODES


def add_dynamic_workflow_node(node: WorkflowNode) -> str:
    node_id = _get_unique_id_for_node(node)
    node.id = node_id
    WORKFLOW_NODES[node_id] = node
    return node_id


def _get_unique_id_for_node(node: WorkflowNode) -> str:
    if node.id not in WORKFLOW_NODES:
        return node.id
    node_id_suffix = 1
    while node.id + "_" + str(node_id_suffix) in WORKFLOW_NODES:
        node_id_suffix += 1
    return node.id + "_" + str(node_id_suffix)


def _load_workflow_nodes(workflow: WorkflowModel):
    global WORKFLOW_NODES
    WORKFLOW_NODES = {node.id: workflow_node_factory(node) for node in workflow.nodes}


def _workflow_nodes_errors(workflow: dict[str, WorkflowNode]) -> dict[str, str]:
    errors = {}
    node_ids = set(workflow.keys())
    for node in workflow.values():
        for transition in node.transitions:
            try:
                transition.check_error(node_ids)
            except WorkflowParameterError as e:
                errors[f"{node.id} {transition.origin}"] = f"Error in {transition.origin} of node {node.id}: {e}"

    return errors


def _select_transition(cur_node: WorkflowNode, output: ActionNodeOutput, state: StateModel) -> Transition | None:
    trace: list[GuardRecord] = []
    selected = None
    for transition in cur_node.transitions:
        if transition.matches(output, state, trace):
            selected = transition
            break
    state.record_guards(cur_node.id, trace)
    return selected


def _fail(cur_node: WorkflowNode, output: ActionNodeOutput, code: str | None) -> Step:
    # A code that differs from the one the action produced replaces it, but the message the action
    # wrote is kept whenever it still explains that code. See ADR 002.
    if code is not None and code != output.error_code:
        output.error_code = code
        output.error_message = f"Node {cur_node.id} failed: {code}"
    elif output.error_message is None:
        output.error_message = f"Node {cur_node.id} failed: {output.error_code}"
    message = output.error_message or output.error_code or "unknown failure"
    return Step(failure=f"{cur_node.id}: {message}")


def _take(transition: Transition, cur_node: WorkflowNode, output: ActionNodeOutput, state: StateModel) -> Step:
    target = transition.target
    if isinstance(target, NodeTarget):
        returns_here = target.node_id == cur_node.id
        if (transition.attempts or returns_here) and state.attempt_counters.get(
            cur_node.id, 0
        ) < cur_node.config.max_attempts:
            return Step(next_node=cur_node)
        if returns_here:
            return _fail(cur_node, output, ATTEMPTS_EXCEEDED_ERROR)
        return Step(next_node=WORKFLOW_NODES[target.node_id])
    if isinstance(target, FailTarget):
        return _fail(cur_node, output, target.code)
    if isinstance(target, EndTarget):
        return Step()
    raise WorkflowEngineError(f"Unknown transition target: {target!r}")


def _proceed_with_output(output: ActionNodeOutput, cur_node: WorkflowNode, state: StateModel) -> Step:
    transition = _select_transition(cur_node, output, state)
    if transition is not None:
        return _take(transition, cur_node, output, state)

    # Nothing matched. A node that declares a route and takes none of them has failed; a node that
    # only asserts something and passes simply ends the workflow. See ADR 002.
    if cur_node.has_routing():
        return _fail(cur_node, output, output.error_code or NO_TRANSITION_ERROR)
    return Step()


def _set_parameters(state: StateModel, parameters: dict[str, object] | None, override: bool) -> None:
    if parameters is not None:
        for key, value in parameters.items():
            if key not in state.params or override:
                state.add_parameter(key, value)


def _state_hints(state: StateModel) -> list[str]:
    return [
        "Current Workflow State:",
        f"working folder: {state.work_dir}",
        *state.info(),
        *state.info_errors(),
        *state.info_params(),
        *state.info_outputs(),
        *state.info_guards(),
    ]


def start_engine(storage: Storage, output: ActionNodeOutput | None) -> PresentResponse:
    try:
        state, workflow = storage.continue_workflow()
        _load_workflow_nodes(workflow)
    except WorkflowEngineError as e:
        return PresentResponse(
            title="Error in workflow setup",
            description="Workflow nodes is not pass validation.",
            instruction="Please check workflow configuration. In errors - all configuration errors",
            errors={"Exception": str(e)},
            goal=(
                "Fix workflow configuration using information from Errors. "
                "Re run workflow or start new with fixed version of workflow configuration."
            ),
        )

    cur_node = get_workflow_node(state.current_node_id)
    if cur_node is None:
        print(f"Engine stop: Node with id {state.current_node_id} not found in workflow")
        return PresentResponse(
            title="Error in workflow setup",
            description="Current node not found in workflow by id",
            instruction=(
                "Probably workflow session is corrupted. Please check workflow configuration, and try start new session"
            ),
            hints=_state_hints(state),
            errors={f"Current node id: {state.current_node_id}": "not found in workflow"},
        )

    errors = _workflow_nodes_errors(WORKFLOW_NODES)
    if len(errors) > 0:
        return PresentResponse(
            title="Error in workflow setup",
            description="Workflow nodes is not pass validation.",
            instruction="Please check workflow configuration. In errors - all configuration errors",
            hints=_state_hints(state),
            errors=errors,
            goal=(
                "Fix workflow configuration using information from Errors. "
                "Re run workflow or start new with fixed version of workflow configuration."
            ),
        )


    try:
        while cur_node is not None:
            _set_parameters(state, cur_node.set_parameters, cur_node.override_parameters)

            # The action of the node the engine resumes at has not run yet. Running it is not an
            # attempt, so the state is not updated for it.
            if output is not None:
                step = _proceed_with_output(output, cur_node, state)
                next_node = step.next_node
                state.update(cur_node.id, cur_node.config.save_as, output, next_node.id if next_node else None)
                storage.save_state(state)

                if step.failure is not None:
                    print(f"Engine stop: {step.failure}")
                    return PresentResponse(
                        title="Node failed",
                        description="A node did not pass its guards and the workflow cannot continue.",
                        instruction="Check the guard results in the state and the errors below.",
                        hints=_state_hints(state),
                        errors={cur_node.id: step.failure},
                    )

                cur_node = next_node

            if cur_node and isinstance(cur_node.action, BaseAutomaticAction):
                output = cur_node.action.execute(state, output)
            elif cur_node and isinstance(cur_node.action, BaseInteractiveAction):
                return cur_node.action.present(state)

    except WorkflowRuntimeError as e:
        print(f"Engine stop: Exception occurred during workflow execution: {e}")
        return PresentResponse(
            title="Error in workflow execution",
            description="An exception occurred during workflow execution.",
            instruction="Please check Exception in Errors and state,",
            hints=_state_hints(state),
            errors={f"Exception: {type(e).__name__}": str(e)},
        )

    storage.save_state(state)

    return PresentResponse(
        title="Loop finished",
        description="All nodes have been processed, and the workflow has completed.",
        instruction="Workflow execution completed successfully. Check state.",
        hints=_state_hints(state),
    )
