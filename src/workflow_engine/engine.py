from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from workflow_engine.actions.action_present import PresentResponse
from workflow_engine.actions.base_actions import (
    BaseAutomaticAction,
    BaseInteractiveAction,
)
from workflow_engine.answers import Answer, BoundAnswer, bind_answer
from workflow_engine.artifacts_export import (
    DeliverableExport,
    ExportedArtifact,
    copy_named_artifacts,
    export_deliverables_on_completion,
)
from workflow_engine.bootstrap.config_loader import CONFIG_FILE_NAME
from workflow_engine.bootstrap.session_factory import WorkflowSession, WorkflowSessionsFactory
from workflow_engine.bootstrap.storage_fatcory import StorageFactory
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.exceptions import (
    WorkflowAnswerError,
    WorkflowEngineError,
    WorkflowInputError,
    WorkflowParameterError,
    WorkflowRuntimeError,
)
from workflow_engine.inputs import InputAssignment, decode_input_value
from workflow_engine.models.node_record import (
    RECORD_STATUS_COMPLETED,
    RECORD_STATUS_FAILED,
    WRITE_MODE_SAVE_AS,
    NodeRecord,
    ParamWriteRecord,
    RecordPage,
    TransitionRecord,
)
from workflow_engine.models.state import GuardRecord, SessionEvent, SessionEventCode, StateModel, StateReadOnlyView
from workflow_engine.models.workflow import WorkflowModel, WorkflowSource
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.providers.base_provider import FinalizeReason
from workflow_engine.providers.provider_seat import finalize_providers
from workflow_engine.registry.function_registry import FUNCTION_NAME_KEY
from workflow_engine.storage.storage import Storage
from workflow_engine.tools import dict_to_text_lv3
from workflow_engine.transition.base import EndTarget, FailTarget, NodeTarget, Transition
from workflow_engine.workflow import WorkflowNode, workflow_node_factory

NO_TRANSITION_ERROR = "no_transition_matched"
ATTEMPTS_EXCEEDED_ERROR = "max_attempts_exceeded"
VISITS_EXCEEDED_ERROR = "max_visits_exceeded"


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


_FINALIZE_REASONS: MappingProxyType[SessionEventCode, FinalizeReason] = MappingProxyType(
    {
        SessionEventCode.WORKFLOW_COMPLETED: FinalizeReason.COMPLETED,
        SessionEventCode.WORKFLOW_FAILED: FinalizeReason.FAILED,
        SessionEventCode.WORKFLOW_SETUP_FAILED: FinalizeReason.FAILED,
        SessionEventCode.WORKFLOW_PAUSED_INTERACTIVE: FinalizeReason.PAUSED,
        SessionEventCode.WORKFLOW_PAUSED_LIMIT: FinalizeReason.PAUSED,
        SessionEventCode.WORKFLOW_PAUSED_SAFETY_LIMIT: FinalizeReason.PAUSED,
    }
)


def _finalize_reason(state: StateModel) -> FinalizeReason:
    """How the run ended, in the terms an adapter is told. See ADR 014 §2.

    The outcome is read from the last event the run recorded, the way the completion export reads
    it. An outcome the map does not name means the run left by a path that recorded nothing, which
    is what `ABORTED` says.
    """
    code = state.get_last_event_code()
    return _FINALIZE_REASONS.get(code, FinalizeReason.ABORTED) if code is not None else FinalizeReason.ABORTED


def _function_name(node: WorkflowNode) -> str | None:
    """The registered function a function-wrapping action runs, where the node names one. See ADR 021 §1."""
    name = node.config.action_parameters.get(FUNCTION_NAME_KEY)
    return name if isinstance(name, str) else None


def _transition_record(step: Step, output: ActionNodeOutput) -> TransitionRecord:
    """Where the visit went: to a node, into a failure, or to the end of the workflow."""
    if step.failure is not None:
        return TransitionRecord.to_failure(output.error_code)
    if step.next_node is not None:
        return TransitionRecord.to_node(step.next_node.id)
    return TransitionRecord.to_end()


def _applied_write_records(output: ActionNodeOutput, state: StateModel, applied: list[str]) -> list[ParamWriteRecord]:
    """Name each applied write with the codec the value landed under and the mode it was written in."""
    records = []
    for name in applied:
        parameter = state.params.get(name)
        write = output.param_writes.get(name)
        if parameter is None:
            continue
        mode = write.mode.name if write is not None else WRITE_MODE_SAVE_AS
        records.append(ParamWriteRecord(name=name, codec=parameter.codec.type_name(), mode=mode))
    return records


def _record_visit(
    storage: Storage,
    state: StateModel,
    node: WorkflowNode,
    output: ActionNodeOutput,
    step: Step,
    ordinals: tuple[int, int],
    applied: list[str],
) -> None:
    """Append the record of one concluded visit, after the state it describes has been saved.

    The order is the crash semantics of ADR 021 §2: the state is authoritative and is written first.
    A trail whose last record is missing is an incomplete account of a run whose state is still
    exact, which is tolerable in evidence; a record ahead of the state would be an account of effects
    that never took hold, which is not.

    A visit whose action produced an error code is recorded as failed even when a guard routes the
    run onwards from it: the status says what happened in the node, and the transition says where the
    run went next. That is how a retry loop reads back as the failures it actually made.
    """
    visit, attempt = ordinals
    storage.append_record(
        state.session_id,
        NodeRecord(
            node_id=node.id,
            action=node.config.action_type,
            function=_function_name(node),
            status=RECORD_STATUS_FAILED if output.error_code is not None else RECORD_STATUS_COMPLETED,
            error_code=output.error_code,
            visit=visit,
            attempt=attempt,
            guards=list(state.guard_results.get(node.id, [])),
            transition=_transition_record(step, output),
            writes=_applied_write_records(output, state, applied),
            artifacts=list(output.artifacts),
            details=dict(output.details),
        ),
    )


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


def _visit_cap_reached(node: WorkflowNode, state: StateModel) -> bool:
    """Whether the node has already completed the visits it declared. See ADR 017 §1.

    ``visit_counters`` count departures, so they hold the completed visits and the node runs exactly
    ``max_visits`` times. A re-presented question consumes no visit (ADR 013 §6), which is why asking
    the same question again can never move this answer.
    """
    max_visits = node.config.max_visits
    return max_visits is not None and state.visit_counters.get(node.id, 0) >= max_visits


def _visit_cap_response(node: WorkflowNode, state: StateModel, storage: Storage) -> PresentResponse:
    """Fail the run at the node the cap belongs to, before its action runs.

    The failure is the workflow's, not the node's: the check precedes the action, so there is no
    output for the node's own transitions to route on, and the code is reported the way
    ``max_attempts_exceeded`` is. See ADR 017 §3.
    """
    visits = state.visit_counters.get(node.id, 0)
    failure = f"{node.id}: Node {node.id} failed: {VISITS_EXCEEDED_ERROR} after {visits} visits"
    state.record_node_error(node.id, VISITS_EXCEEDED_ERROR, f"Node {node.id} failed: {VISITS_EXCEEDED_ERROR}")
    state.record_session_event(
        SessionEvent.engine_event(
            SessionEventCode.WORKFLOW_FAILED,
            {"node_id": node.id, "failure": failure, "visits": visits, "max_visits": node.config.max_visits},
        )
    )
    storage.save_state(state)
    # A refusal on entry is a visit that concluded before its action ran, and the trail says so: the
    # record names the visit the node was not allowed to make. See ADR 021 §1.
    visit, attempt = state.visit_ordinals(node.id)
    storage.append_record(
        state.session_id,
        NodeRecord(
            node_id=node.id,
            action=node.config.action_type,
            function=_function_name(node),
            status=RECORD_STATUS_FAILED,
            error_code=VISITS_EXCEEDED_ERROR,
            visit=visit,
            attempt=attempt,
            transition=TransitionRecord.to_failure(VISITS_EXCEEDED_ERROR),
        ),
    )
    return PresentResponse(
        title="Node visit cap reached",
        description=f"Node '{node.id}' has completed the {node.config.max_visits} visits it declares "
        f"in 'max_visits', so it was not entered again and the workflow failed.",
        instruction="Fix the loop that keeps returning to this node, or raise its 'max_visits' if the "
        "run legitimately needs more passes through it.",
        hints=_state_hints(state),
        errors={node.id: failure},
    )


def _start_engine(
    workflow_nodes: MappingProxyType[str, WorkflowNode],
    storage: Storage,
    state: StateModel,
    output: ActionNodeOutput | None,
    hard_max_nodes_visited: int,
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
            if state.nodes_visited >= hard_max_nodes_visited:
                state.record_session_event(
                    SessionEvent.engine_event(
                        SessionEventCode.WORKFLOW_PAUSED_SAFETY_LIMIT,
                        {
                            "node_id": cur_node.id,
                            "nodes_visited": state.nodes_visited,
                            "max_nodes_visited": state.max_nodes_visited,
                            "hard_max_nodes_visited": hard_max_nodes_visited,
                        },
                    )
                )
                storage.save_state(state)
                return PresentResponse(
                    title="Workflow safety cap reached",
                    description=f"The workflow has reached the global hard safety cap: "
                    f"{state.nodes_visited}/{hard_max_nodes_visited} nodes visited. "
                    f"A session with no soft limit is still bounded by this cap.",
                    instruction=f"The cap cannot be raised by a session command. Check the visit counters "
                    f"in the state for a likely loop. To continue a legitimately long run, raise "
                    f"'hard_max_nodes_visited' in '{CONFIG_FILE_NAME}' and resume the session.",
                    hints=_state_hints(state),
                    errors={cur_node.id: "Workflow hard safety cap reached"},
                )
            _set_parameters(state, cur_node.set_parameters, cur_node.override_parameters)
            state_read_only = StateReadOnlyView.from_state(state)
            # The action of the node the engine resumes at has not run yet. Running it is not an
            # attempt, so the state is not updated for it.
            if output is not None:
                if isinstance(cur_node.action, BaseInteractiveAction):
                    # The output at an interactive node is an accepted answer, and this is the only
                    # place one arrives: the action may compute on it before its own guards see it.
                    # Here the function reads the state view the guards read and returns the output
                    # `state.update` applies, so there is no second ordering question. See ADR 015 §3.
                    output = cur_node.action.process_answer(state_read_only, output)
                ordinals = state.visit_ordinals(cur_node.id)
                step = _proceed_with_output(workflow_nodes, output, cur_node, state, state_read_only)
                next_node = step.next_node
                applied = state.update(
                    cur_node.id, cur_node.config.save_as, output, next_node.id if next_node else None
                )
                state_read_only = StateReadOnlyView.from_state(state)
                storage.save_state(state)
                _record_visit(storage, state, cur_node, output, step, ordinals, applied)

                if step.failure is not None:
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

            # The entry check of the per-node cap, and the reason it sits here rather than at the top
            # of the loop: the node about to run is only known once the transition has been taken, and
            # at the top of an iteration `cur_node` is still the node whose output is being routed.
            # See ADR 017 §1.
            if cur_node is not None and _visit_cap_reached(cur_node, state):
                return _visit_cap_response(cur_node, state, storage)

            if cur_node and isinstance(cur_node.action, BaseAutomaticAction):
                output = cur_node.action.execute(state_read_only, output)
            elif cur_node and isinstance(cur_node.action, BaseInteractiveAction):
                # The run stops at the question. The paused position needs no state field of its own:
                # it is the current node, and the built node says whether it is interactive. See ADR 013 §3.
                response = cur_node.action.present(state_read_only)
                state.record_session_event(
                    SessionEvent.engine_event(
                        SessionEventCode.WORKFLOW_PAUSED_INTERACTIVE,
                        {
                            "node_id": cur_node.id,
                            "answer": [
                                declaration.name for declaration in cur_node.action.answer_contract().declarations
                            ],
                        },
                    )
                )
                storage.save_state(state)
                return response

    except WorkflowRuntimeError as e:
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


def _answered_event(state: StateModel, answer: Answer, bound: BoundAnswer) -> SessionEvent:
    """Journal the answer as an operator-side event. See ADR 013 §9.

    It records who answered and which names were bound with which codecs, never the values, mirroring
    ``inputs_set``. The label rides in the details because ``SessionEvent.actor`` stays the two-valued
    engine/operator distinction of ADR 006: who supplied an answer is a property of the answer.

    ``visit`` and ``attempt`` place the answer in the run: the visit of the node it belongs to, and the
    ordinal of the answer within that visit. The counters keep their enforcement semantics — attempts
    reset on departure — so the retries that reset away are recorded here instead of being
    reconstructible only by counting events between visit boundaries. See ADR 017 §4.
    """
    node_id = state.current_node_id
    visit, attempt = state.visit_ordinals(node_id)
    details: dict[str, object] = {
        "node_id": node_id,
        "visit": visit,
        "attempt": attempt,
        "status": answer.status.value,
        "actor": answer.actor,
        "names": list(bound.codecs),
        "codecs": bound.codecs,
    }
    if answer.error_code is not None:
        details["error_code"] = answer.error_code
    return SessionEvent.operator_event(SessionEventCode.INTERACTIVE_ANSWERED, details)


class WorkflowEngine:
    storage_factory: StorageFactory
    session_factory: WorkflowSessionsFactory
    components: dict[str, dict[str, dict[str, str]]]
    hard_max_nodes_visited: int
    export_dir: str | None
    runtime: SessionRuntime | None
    last_export: DeliverableExport | None

    def __init__(
        self,
        storage_factory: StorageFactory,
        session_factory: WorkflowSessionsFactory,
        components: dict[str, dict[str, dict[str, str]]],
        hard_max_nodes_visited: int,
        export_dir: str | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.storage_factory = storage_factory
        self.components = components
        self.hard_max_nodes_visited = hard_max_nodes_visited
        self.export_dir = export_dir
        self.runtime = None
        self.last_export = None

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
        state = session.create_state(workflow, workflow_dir=workflow_path.expanduser().resolve(strict=False).parent)
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
        self, session_id: str, answer: Answer | None = None, export_dir: str | None = None
    ) -> tuple[PresentResponse, StateModel]:
        """Start or continue a workflow session, optionally answering the node it is paused at.

        An answer is validated before anything is journaled, so a refused one leaves the run exactly as
        it was (ADR 013 §5). Resuming a paused interactive node without an answer presents the same
        question again, consuming no attempt and no visit (§6).
        """
        self.last_export = None
        released = False
        try:
            runtime = self._acquire(session_id)
            if runtime.setup_error is not None:
                runtime.state.record_session_event(
                    SessionEvent.engine_event(
                        SessionEventCode.WORKFLOW_SETUP_FAILED,
                        {
                            "node_id": runtime.state.current_node_id,
                            "title": runtime.setup_error.title,
                            "error_count": len(runtime.setup_error.errors or {}),
                        },
                    )
                )
                self._commit(runtime)
                released = True
                self._release_providers(_finalize_reason(runtime.state), runtime.setup_error)
                return runtime.setup_error, runtime.state

            self._require_bound_inputs(runtime, session_id)
            bound = self._accept_answer(runtime, answer) if answer is not None else None

            runtime.state.record_session_event(_run_entry_event(runtime.state))
            if answer is not None and bound is not None:
                runtime.state.record_session_event(_answered_event(runtime.state, answer, bound))
            self._commit(runtime)
            output = bound.output if bound is not None else None
            response = _start_engine(runtime.nodes, runtime.storage, runtime.state, output, self.hard_max_nodes_visited)
            # The outcome is read before the export, which records events of its own after it.
            reason = _finalize_reason(runtime.state)
            self._commit(runtime)
            self._export_on_completion(runtime, export_dir)
            released = True
            self._release_providers(reason, response)
            return response, runtime.state
        finally:
            # A run that left by an unforeseen path still releases what its adapters hold.
            if not released:
                self._release_providers(FinalizeReason.ABORTED)

    def _release_providers(self, reason: FinalizeReason, response: PresentResponse | None = None) -> None:
        """Finalize the seated provider adapters, reporting an adapter that failed to release.

        The failure is added to the response under a key of its own and changes neither the outcome
        of the run nor the exit code: the workflow has already reached its end, and a model left
        resident on a server is an operator's problem rather than a failed workflow. See ADR 014 §2.
        """
        failures = finalize_providers(reason)
        if failures and response is not None:
            reported = {f"provider:{name}": message for name, message in failures.items()}
            response.errors = {**(response.errors or {}), **reported}

    def _export_on_completion(self, runtime: SessionRuntime, export_dir_override: str | None) -> None:
        """Export declared deliverables when the run completed and a destination is resolved.

        Precedence: the per-call override (the CLI option), then the configured ``export_dir``. Only
        a terminal ``workflow_completed`` triggers export; paused and failed runs never auto-export.
        See ADR 011.
        """
        if runtime.state.get_last_event_code() != SessionEventCode.WORKFLOW_COMPLETED:
            return
        destination = export_dir_override or self.export_dir
        if not destination or not runtime.workflow.deliverables:
            return
        self.last_export = export_deliverables_on_completion(
            runtime.state, runtime.workflow.deliverables, Path(destination)
        )
        self._commit(runtime)

    def get_last_export(self) -> DeliverableExport | None:
        """The completion export of the last run started through this engine, or None if none ran.

        A caller that asked for an export learns the destination from the command result instead of
        having to read the session event journal. See ADR 011.
        """
        return self.last_export

    def set_session_limits(self, session_id: str, max_nodes_visited: int) -> StateReadOnlyView:
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
        return StateReadOnlyView.from_state(runtime.state)

    def get_status(self, session_id: str) -> StateReadOnlyView:
        runtime = self._acquire(session_id)
        return StateReadOnlyView.from_state(runtime.state)

    def get_records(self, session_id: str, node_id: str | None = None, tail: int | None = None) -> RecordPage:
        """The node records of a session, filtered by node first and bounded by tail last.

        The trail is read from storage and never from the state: no engine logic reads a record back
        during a run, so this exists for the reader who explains the run afterwards. See ADR 021 §4.
        """
        runtime = self._acquire(session_id)
        return runtime.storage.load_records(session_id, node_id=node_id, tail=tail)

    def get_deliverables(self, session_id: str) -> list[str]:
        runtime = self._acquire(session_id)
        return list(runtime.workflow.deliverables)

    def get_inputs(self, session_id: str) -> list[dict[str, object]]:
        """The declared input interface of a session's workflow, for introspection. See ADR 012."""
        runtime = self._acquire(session_id)
        return [declaration.to_dict() for declaration in runtime.workflow.inputs]

    def set_inputs(self, session_id: str, assignments: list[InputAssignment]) -> StateReadOnlyView:
        """Bind typed input values to an unstarted session and journal the binding. See ADR 012.

        Only names declared in the workflow's ``inputs`` are accepted; a duplicate name in one call, an
        undeclared name, a decode failure, or binding after the run has started is a command error. Values
        land in ``state.params`` as ``SET`` writes through the normal write path; the recorded event carries
        the bound names and resolved codec names, never the values.
        """
        runtime = self._acquire(session_id)
        state = runtime.state
        if state.has_session_event(SessionEventCode.WORKFLOW_STARTED):
            raise WorkflowInputError(f"Cannot set inputs on session {session_id}: the run has already started")
        declared = {declaration.name: declaration for declaration in runtime.workflow.inputs}
        seen: set[str] = set()
        names: list[str] = []
        codecs: dict[str, str | None] = {}
        for assignment in assignments:
            declaration = declared.get(assignment.name)
            if declaration is None:
                raise WorkflowInputError(f"Undeclared input '{assignment.name}'. Declared inputs: {sorted(declared)}")
            if assignment.name in seen:
                raise WorkflowInputError(f"Duplicate input '{assignment.name}' in one invocation")
            seen.add(assignment.name)
            value, codec_name = decode_input_value(assignment, declaration)
            error = state._param_write(
                assignment.name,
                ParamWrite(mode=WriteParamMode.SET, value=value, allow_overwrite=True),
                # An input is bound before the first node runs, so the node the session starts at is
                # the closest thing to a producer this write has.
                state.current_node_id,
            )
            if error is not None:
                raise WorkflowInputError(f"Cannot bind input '{assignment.name}': [{error[0]}] {error[1]}")
            names.append(assignment.name)
            codecs[assignment.name] = codec_name
        state.record_session_event(
            SessionEvent.operator_event(SessionEventCode.INPUTS_SET, {"names": names, "codecs": codecs})
        )
        self._commit(runtime)
        return StateReadOnlyView.from_state(state)

    @staticmethod
    def _accept_answer(runtime: SessionRuntime, answer: Answer) -> BoundAnswer:
        """Accept an answer only from a run that is actually waiting for one. See ADR 013 §5.

        Both halves of the precondition are needed: the node must be the kind that asks, and the run
        must be stopped at its question. An answer to a node that did not ask is the fabricated node
        output ADR 012 removed. Every refusal raises before anything is applied or journaled, the way a
        refused ``set-input`` behaves.
        """
        state = runtime.state
        node = _get_workflow_node(runtime.nodes, state.current_node_id)
        action = node.action if node is not None else None
        if not isinstance(action, BaseInteractiveAction):
            raise WorkflowAnswerError(
                f"Node '{state.current_node_id}' of session {state.session_id} asked nothing: "
                f"an answer is accepted only at an interactive node"
            )
        last_event = state.get_last_event_code()
        if last_event is not SessionEventCode.WORKFLOW_PAUSED_INTERACTIVE:
            raise WorkflowAnswerError(
                f"Session {state.session_id} is not waiting for an answer: the last event is "
                f"'{last_event.value}', not '{SessionEventCode.WORKFLOW_PAUSED_INTERACTIVE.value}'"
            )
        return bind_answer(answer, action.answer_contract())

    @staticmethod
    def _require_bound_inputs(runtime: SessionRuntime, session_id: str) -> None:
        """Fail the first start of a session when a ``required`` input is unbound. See ADR 012.

        Journaled as ``workflow_setup_failed`` with the missing names, then raised so the CLI reports a
        command error (exit code 4). Runs only on the first execution, keyed off the journal, not counters.
        """
        state = runtime.state
        if state.has_session_event(SessionEventCode.WORKFLOW_STARTED):
            return
        missing = [
            declaration.name
            for declaration in runtime.workflow.inputs
            if declaration.required and declaration.name not in state.params
        ]
        if not missing:
            return
        state.record_session_event(
            SessionEvent.engine_event(
                SessionEventCode.WORKFLOW_SETUP_FAILED,
                {"node_id": state.current_node_id, "missing_inputs": missing},
            )
        )
        WorkflowEngine._commit(runtime)
        raise WorkflowInputError(f"Cannot start session {session_id}: required inputs not bound: {missing}")

    def export_artifact(
        self,
        session_id: str,
        target_dir: Path,
        artifact_name: str | None = None,
        all_deliverables: bool = False,
    ) -> list[ExportedArtifact]:
        """Copy one named artifact, or all declared deliverables, of an existing session out.

        The manual salvage path: it works for completed, paused and failed sessions and records no
        session events. A missing session, unknown name, or an ``--all`` on a definition that
        declares no deliverables is a resolution error. See ADR 011.
        """
        runtime = self._acquire(session_id)
        if all_deliverables:
            names = runtime.workflow.deliverables
            if not names:
                raise WorkflowEngineError(f"Session {session_id} declares no deliverables to export with --all")
        else:
            if artifact_name is None:
                raise WorkflowEngineError("An artifact name or --all is required")
            names = (artifact_name,)
        return copy_named_artifacts(runtime.state, names, target_dir)
