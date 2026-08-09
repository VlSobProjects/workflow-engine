from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from workflow_engine.actions.action_present import PresentResponse
from workflow_engine.actions.base_actions import (
    BaseAutomaticAction,
    BaseInteractiveAction,
)
from workflow_engine.bootstrap.session_factory import WorkflowSession, WorkflowSessionsFactory
from workflow_engine.bootstrap.storage_fatcory import StorageFactory
from workflow_engine.exceptions import WorkflowEngineError, WorkflowParameterError, WorkflowRuntimeError
from workflow_engine.models.state import GuardRecord, SessionEvent, SessionEventCode, StateModel, StateReadOnlyView
from workflow_engine.models.workflow import WorkflowModel, WorkflowSource
from workflow_engine.output import ActionNodeOutput
from workflow_engine.storage.storage import Storage
from workflow_engine.tools import dict_to_text_lv3
from workflow_engine.transition.base import EndTarget, FailTarget, NodeTarget, Transition
from workflow_engine.workflow import WorkflowNode, workflow_node_factory

NO_TRANSITION_ERROR = "no_transition_matched"
ATTEMPTS_EXCEEDED_ERROR = "max_attempts_exceeded"


@dataclass(frozen=True, slots=True)
class Step:
    """What the engine does after a node: continue, end, or fail."""

    next_node: WorkflowNode | None = None
    failure: str | None = None


def _get_workflow_node(workflow_nodes: MappingProxyType[str, WorkflowNode], node_id: str) -> WorkflowNode | None:
    return workflow_nodes.get(node_id)


def _is_workflow_node(workflow_nodes: MappingProxyType[str, WorkflowNode], node_id: str) -> bool:
    return node_id in workflow_nodes


def _get_unique_id_for_node(workflow_nodes: dict[str, WorkflowNode], node: WorkflowNode) -> str:
    if node.id not in workflow_nodes:
        return node.id
    node_id_suffix = 1
    while node.id + "_" + str(node_id_suffix) in workflow_nodes:
        node_id_suffix += 1
    return node.id + "_" + str(node_id_suffix)


def _load_workflow_nodes(workflow_nodes: dict[str, WorkflowNode], workflow: WorkflowModel) -> dict[str, str]:
    errors: dict[str, str] = {}
    for node in workflow.nodes:
        try:
            workflow_nodes[node.id] = workflow_node_factory(node)
        except WorkflowEngineError as e:
            errors[node.id] = str(e)
    return errors


def _workflow_nodes_errors(workflow: MappingProxyType[str, WorkflowNode]) -> dict[str, str]:
    errors = {}
    node_ids = set(workflow.keys())
    for node in workflow.values():
        for transition in node.transitions:
            try:
                transition.check_error(node_ids)
            except WorkflowParameterError as e:
                errors[f"{node.id} {transition.origin}"] = f"Error in {transition.origin} of node {node.id}: {e}"

    return errors


def _select_transition(
    cur_node: WorkflowNode, output: ActionNodeOutput, state_read_only: StateReadOnlyView, state: StateModel
) -> Transition | None:
    trace: list[GuardRecord] = []
    selected = None
    for transition in cur_node.transitions:
        if transition.matches(output, state_read_only, trace):
            selected = transition
            break
    state.record_guards(cur_node.id, trace)
    return selected


def _fail(cur_node: WorkflowNode, output: ActionNodeOutput, code: str | None) -> Step:
    # A code that differs from the one the action produced replaces it, but the message the action
    # wrote is kept whenever it still explains that code. See ADR 002.
    if code is not None and code != output.error_code:
        output.error_code = code
        output.error_msg = f"Node {cur_node.id} failed: {code}"
    elif output.error_msg is None:
        output.error_msg = f"Node {cur_node.id} failed: {output.error_code}"
    message = output.error_msg or output.error_code or "unknown failure"
    return Step(failure=f"{cur_node.id}: {message}")


def _take(
    workflow_nodes: MappingProxyType[str, WorkflowNode],
    transition: Transition,
    cur_node: WorkflowNode,
    output: ActionNodeOutput,
    state: StateModel,
) -> Step:
    target = transition.target
    if isinstance(target, NodeTarget):
        returns_here = target.node_id == cur_node.id
        if (transition.attempts or returns_here) and state.attempt_counters.get(
            cur_node.id, 0
        ) < cur_node.config.max_attempts:
            return Step(next_node=cur_node)
        if returns_here:
            return _fail(cur_node, output, ATTEMPTS_EXCEEDED_ERROR)
        return Step(next_node=workflow_nodes[target.node_id])
    if isinstance(target, FailTarget):
        return _fail(cur_node, output, target.code)
    if isinstance(target, EndTarget):
        return Step()
    raise WorkflowEngineError(f"Unknown transition target: {target!r}")


def _proceed_with_output(
    workflow_nodes: MappingProxyType[str, WorkflowNode],
    output: ActionNodeOutput,
    cur_node: WorkflowNode,
    state: StateModel,
    state_read_only: StateReadOnlyView,
) -> Step:
    transition = _select_transition(cur_node, output, state_read_only, state)
    if transition is not None:
        return _take(workflow_nodes, transition, cur_node, output, state)

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


def _start_engine(
    workflow_nodes: MappingProxyType[str, WorkflowNode],
    storage: Storage,
    state: StateModel,
    output: ActionNodeOutput | None,
) -> PresentResponse:
    cur_node = _get_workflow_node(workflow_nodes, state.current_node_id)
    try:
        while cur_node is not None:
            if state.is_max_node_exceeded():
                state.record_session_event(
                    SessionEvent.engine_event(
                        SessionEventCode.WORKFLOW_PAUSED_LIMIT,
                        {
                            "node_id": cur_node.id,
                            "nodes_visited": state.nodes_visited,
                            "max_nodes_visited": state.max_nodes_visited,
                        },
                    )
                )
                storage.save_state(state)
                return PresentResponse(
                    title="Workflow budget exceeded",
                    description=f"The workflow has exceeded the maximum number of nodes "
                    f"visited: {state.nodes_visited}/{state.max_nodes_visited}",
                    instruction="You can change max node exceeded Workflow engine call set_session_limits",
                    hints=_state_hints(state),
                    errors={cur_node.id: "Workflow max node exceeded"},
                )
            _set_parameters(state, cur_node.set_parameters, cur_node.override_parameters)
            state_read_only = StateReadOnlyView.from_state(state)
            # The action of the node the engine resumes at has not run yet. Running it is not an
            # attempt, so the state is not updated for it.
            if output is not None:
                step = _proceed_with_output(workflow_nodes, output, cur_node, state, state_read_only)
                next_node = step.next_node
                state.update(cur_node.id, cur_node.config.save_as, output, next_node.id if next_node else None)
                state_read_only = StateReadOnlyView.from_state(state)
                storage.save_state(state)

                if step.failure is not None:
                    print(f"Engine stop: {step.failure}")
                    state.record_session_event(
                        SessionEvent.engine_event(
                            SessionEventCode.WORKFLOW_FAILED, {"node_id": cur_node.id, "failure": step.failure}
                        )
                    )
                    storage.save_state(state)
                    return PresentResponse(
                        title="Node failed",
                        description="A node did not pass its guards and the workflow cannot continue.",
                        instruction="Check the guard results in the state and the errors below.",
                        hints=_state_hints(state),
                        errors={cur_node.id: step.failure},
                    )

                cur_node = next_node

            if cur_node and isinstance(cur_node.action, BaseAutomaticAction):
                output = cur_node.action.execute(state_read_only, output)
            elif cur_node and isinstance(cur_node.action, BaseInteractiveAction):
                return cur_node.action.present(state_read_only)

    except WorkflowRuntimeError as e:
        print(f"Engine stop: Exception occurred during workflow execution: {e}")
        state.record_session_event(
            SessionEvent.engine_event(
                SessionEventCode.WORKFLOW_FAILED,
                {"node_id": state.current_node_id, "exception": type(e).__name__, "message": str(e)},
            )
        )
        storage.save_state(state)
        return PresentResponse(
            title="Error in workflow execution",
            description="An exception occurred during workflow execution.",
            instruction="Please check Exception in Errors and state,",
            hints=_state_hints(state),
            errors={f"Exception: {type(e).__name__}": str(e)},
        )

    state.record_session_event(
        SessionEvent.engine_event(
            SessionEventCode.WORKFLOW_COMPLETED,
            {"node_id": state.current_node_id, "nodes_visited": state.nodes_visited},
        )
    )
    storage.save_state(state)

    return PresentResponse(
        title="Loop finished",
        description="All nodes have been processed, and the workflow has completed.",
        instruction="Workflow execution completed successfully. Check state.",
        hints=_state_hints(state),
    )


@dataclass(frozen=True, slots=True)
class SessionRuntime:
    """Everything one session needs to run: loaded once, cached by the engine, never partially filled.

    `setup_error` is the deferred answer for a session whose workflow does not validate: the runtime
    exists and its state can be reported, but it must not be executed.
    """

    session: WorkflowSession
    storage: Storage
    state: StateModel
    workflow: WorkflowModel
    nodes: MappingProxyType[str, WorkflowNode]
    setup_error: PresentResponse | None = None


def _build_workflow_nodes(
    workflow: WorkflowModel, state: StateModel
) -> tuple[MappingProxyType[str, WorkflowNode], PresentResponse | None]:
    empty: MappingProxyType[str, WorkflowNode] = MappingProxyType({})
    nodes: dict[str, WorkflowNode] = {}
    errors = _load_workflow_nodes(nodes, workflow)
    if len(errors) > 0:
        return empty, PresentResponse(
            title="Errors in workflow configuration",
            description="Validation of workflow nodes failed",
            instruction="Please check errors in workflow configuration, and try to start a new session",
            hints=_state_hints(state),
            errors=errors,
        )

    if _get_workflow_node(MappingProxyType(nodes), state.current_node_id) is None:
        print(f"Engine stop: Node with id {state.current_node_id} not found in workflow")
        return empty, PresentResponse(
            title="Error in workflow setup",
            description="Current node not found in workflow by id",
            instruction=(
                "Probably workflow session is corrupted. Please check workflow configuration, and try start new session"
            ),
            hints=_state_hints(state),
            errors={f"Current node id: {state.current_node_id}": "not found in workflow"},
        )

    errors = _workflow_nodes_errors(MappingProxyType(nodes))
    if len(errors) > 0:
        return empty, PresentResponse(
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
    return MappingProxyType(nodes), None


def _build_runtime(
    session: WorkflowSession, storage: Storage, state: StateModel, workflow: WorkflowModel
) -> SessionRuntime:
    nodes, setup_error = _build_workflow_nodes(workflow, state)
    return SessionRuntime(
        session=session, storage=storage, state=state, workflow=workflow, nodes=nodes, setup_error=setup_error
    )


def _run_entry_event(state: StateModel) -> SessionEvent:
    """A session is started once and resumed every time after that.

    The distinction is read from the persisted journal, so it holds across engine instances and process
    restarts. Node counters cannot answer it: a run that stops at an interactive first node leaves them
    untouched. See ADR 006.
    """

    if state.has_session_event(SessionEventCode.WORKFLOW_STARTED):
        return SessionEvent.operator_event(
            SessionEventCode.WORKFLOW_RESUMED,
            {"session_id": state.session_id, "node_id": state.current_node_id},
        )
    return SessionEvent.operator_event(
        SessionEventCode.WORKFLOW_STARTED,
        {"session_id": state.session_id, "node_id": state.current_node_id},
    )


class WorkflowEngine:
    storage_factory: StorageFactory
    session_factory: WorkflowSessionsFactory
    components: dict[str, dict[str, dict[str, str]]]
    runtime: SessionRuntime | None

    def __init__(
        self,
        storage_factory: StorageFactory,
        session_factory: WorkflowSessionsFactory,
        components: dict[str, dict[str, dict[str, str]]],
    ) -> None:
        self.session_factory = session_factory
        self.storage_factory = storage_factory
        self.components = components
        self.runtime = None

    @property
    def session(self) -> WorkflowSession | None:
        return self.runtime.session if self.runtime is not None else None

    @property
    def storage(self) -> Storage | None:
        return self.runtime.storage if self.runtime is not None else None

    @property
    def workflow_nodes(self) -> MappingProxyType[str, WorkflowNode]:
        return self.runtime.nodes if self.runtime is not None else MappingProxyType({})

    def _load(self, session_id: str) -> SessionRuntime:
        """Load a session with the storage recorded in the session, not the current configuration.

        Loading has no side effect on the journal: what an external call means is decided by the caller.
        """

        session = self.session_factory.load_session(session_id)
        storage = self.storage_factory.build_storage(session.storage)
        state = storage.load_state(session.session_id)
        if not session.is_same(state):
            raise WorkflowRuntimeError(
                f"Session data mismatch: session {session.to_dict()} does not match state {state.session_view()}"
            )
        return _build_runtime(session, storage, state, storage.load_workflow(session_id))

    def _acquire(self, session_id: str) -> SessionRuntime:
        """The cached runtime is a cache and nothing else: another session id always means a fresh load."""

        runtime = self.runtime
        if runtime is not None and runtime.state.session_id == session_id:
            return runtime
        runtime = self._load(session_id)
        self.runtime = runtime
        return runtime

    @staticmethod
    def _commit(runtime: SessionRuntime) -> None:
        runtime.storage.save_state(runtime.state)

    def init_new_session(self, workflow_path: Path) -> str:
        if self.runtime is not None:
            raise WorkflowEngineError(
                f"Cannot start a new session while another session is active. "
                f"Current session ID: {self.runtime.state.session_id}"
            )
        workflow = WorkflowSource.upload_workflow_from_file(workflow_path)
        session = self.session_factory.new_session(workflow, self.storage_factory.storage_config())
        storage = self.storage_factory.build_storage(session.storage)
        state = session.create_state(workflow)
        storage.save_workflow(state.session_id, workflow)
        runtime = _build_runtime(session, storage, state, workflow)
        self.runtime = runtime
        state.record_session_event(
            SessionEvent.operator_event(
                SessionEventCode.SESSION_CREATED,
                {"session_id": state.session_id, "flow_id": workflow.flow_id, "node_id": state.current_node_id},
            )
        )
        self._commit(runtime)
        return state.session_id

    def components_report(self) -> str:
        return dict_to_text_lv3("Workflow Engine Components", self.components, 0, 4)

    def start_workflow(
        self, session_id: str, output: ActionNodeOutput | None = None
    ) -> tuple[PresentResponse, StateModel]:
        """Start or continue a workflow session."""
        runtime = self._acquire(session_id)
        if runtime.setup_error is not None:
            return runtime.setup_error, runtime.state

        runtime.state.record_session_event(_run_entry_event(runtime.state))
        self._commit(runtime)
        response = _start_engine(runtime.nodes, runtime.storage, runtime.state, output)
        self._commit(runtime)
        return response, runtime.state

    def set_session_limits(self, session_id: str, max_nodes_visited: int) -> None:
        runtime = self._acquire(session_id)
        state = runtime.state
        limit_before = state.max_nodes_visited
        if max_nodes_visited == 0:
            state.max_nodes_visited = 0
        elif max_nodes_visited < state.max_nodes_visited:
            raise WorkflowEngineError(
                f"Cannot set max_nodes_visited to {max_nodes_visited} "
                f"because it is less than the current max_nodes_visited {state.max_nodes_visited}"
            )
        else:
            state.max_nodes_visited = max_nodes_visited
        state.record_session_event(
            SessionEvent.operator_event(
                SessionEventCode.OPERATOR_LIMIT_UPDATED,
                {
                    "nodes_visited": state.nodes_visited,
                    "limit_before": limit_before,
                    "limit_after": state.max_nodes_visited,
                },
            )
        )
        self._commit(runtime)
