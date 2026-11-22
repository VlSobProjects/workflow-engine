"""The fact model of one session: what the report shows, decided in Python. See ADR 022 §3 and §4.

The model is the interface between the engine and its own viewer, both shipped in one package. Every
engine fact is settled here — the build of a node, the transition a visit took, the rendering of a
value — so the viewer presents and never computes. It is internal, not a published contract, and
carries ``schema_version`` so a document states which model it holds.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from workflow_engine.actions.action_ask import AskAction
from workflow_engine.answers import ANSWER_FAILED
from workflow_engine.engine import VISITS_EXCEEDED_ERROR
from workflow_engine.exceptions import WorkflowEngineError
from workflow_engine.models.node import WorkflowNodeModel
from workflow_engine.models.node_record import NodeRecord
from workflow_engine.models.state import SessionEventCode, StateReadOnlyView
from workflow_engine.models.workflow import WorkflowModel
from workflow_engine.text_interpolation import resolve_template_text
from workflow_engine.tools import render_value_as_text
from workflow_engine.transition.base import EndTarget, FailTarget, NodeTarget, Transition
from workflow_engine.transition.guards import AnyOfGuard, BaseGuard, GroupGuard
from workflow_engine.workflow import build_transitions, workflow_node_factory

SCHEMA_VERSION: Final[str] = "1"

VALUE_CUT: Final[int] = 160
"""Characters of a rendered value the report keeps; a longer value is cut and says so."""

HOME_MARK: Final[str] = "~"

_PRESENTATION_FIELDS: Final[tuple[str, ...]] = ("title", "description", "instruction", "goal", "context")
_PRESENTATION_LISTS: Final[tuple[str, ...]] = ("options", "requirements", "constraints", "examples", "hints")

_OUTCOME_CODES: Final[frozenset[SessionEventCode]] = frozenset(
    {
        SessionEventCode.WORKFLOW_COMPLETED,
        SessionEventCode.WORKFLOW_FAILED,
        SessionEventCode.WORKFLOW_SETUP_FAILED,
        SessionEventCode.WORKFLOW_PAUSED_LIMIT,
        SessionEventCode.WORKFLOW_PAUSED_SAFETY_LIMIT,
        SessionEventCode.WORKFLOW_PAUSED_INTERACTIVE,
    }
)


def _guard_text(guard: BaseGuard) -> str:
    """The guard as a reader sees it: a group names its members, which its own record does not."""
    if isinstance(guard, GroupGuard):
        text = f"{guard.data_keys()[0]}({', '.join(_guard_text(member) for member in guard.guards)})"
        return f"not {text}" if guard.negated else text
    return guard.name()


def _target_fields(transition: Transition) -> dict[str, object]:
    target = transition.target
    if isinstance(target, NodeTarget):
        return {"kind": "node", "target": target.node_id}
    if isinstance(target, FailTarget):
        return {"kind": "fail", "target": target.code}
    if isinstance(target, EndTarget):
        return {"kind": "end", "target": None}
    raise WorkflowEngineError(f"Unknown transition target: {target!r}")


def _effective(transitions: Sequence[Transition]) -> list[dict[str, object]]:
    return [
        {
            "origin": transition.origin,
            "guard": None if transition.guard is None else _guard_text(transition.guard),
            "attempts": transition.attempts,
            **_target_fields(transition),
        }
        for transition in transitions
    ]


def _error_chain(error: BaseException) -> str:
    """The error with every cause under it: the engine wraps the reason a node does not build."""
    messages: list[str] = []
    current: BaseException | None = error
    while current is not None and len(messages) < 8:
        message = str(current) or type(current).__name__
        if message not in messages:
            messages.append(message)
        current = current.__cause__ or current.__context__
    return "; caused by: ".join(messages)


def _build(node: WorkflowNodeModel) -> tuple[list[Transition], str | None]:
    """The effective transitions of a node, built on a copy because a build writes into its configuration.

    When the node cannot be built — a component module that no longer loads — its transitions are
    still built where they can be, since they do not depend on the action; when they cannot either,
    the report keeps the written view alone. The build error is reported either way.
    """
    try:
        return workflow_node_factory(copy.deepcopy(node)).transitions, None
    except WorkflowEngineError as error:
        build_error = _error_chain(error)
    try:
        return build_transitions(copy.deepcopy(node)), build_error
    except WorkflowEngineError:
        return [], build_error


def _replay(guard: BaseGuard, trace: Sequence[dict[str, object]], index: int) -> tuple[int, bool] | None:
    """Consume the records one evaluation of ``guard`` left in a trace: members first, the guard last.

    Returns the position after them and what the guard answered, or None when the trace does not hold
    this evaluation — the trace and the definition then disagree, and nothing is inferred.
    """
    if isinstance(guard, GroupGuard):
        for member in guard.guards:
            step = _replay(member, trace, index)
            if step is None:
                return None
            index, passed = step
            # all_of stops at the first member that fails, any_of at the first that holds.
            if passed == isinstance(guard, AnyOfGuard):
                break
    if index >= len(trace) or trace[index].get("name") != guard.name():
        return None
    return index + 1, bool(trace[index].get("passed"))


def _taken_origin(record: NodeRecord, transitions: Sequence[Transition]) -> str | None:
    """The origin of the transition a visit took, decided by replaying its guard trace.

    A record names the guards it evaluated and where the run went, not which transition was selected:
    the engine took the first transition whose guard held, so the trace is replayed against the
    effective transitions in order. A visit refused on entry evaluated nothing and took no transition.
    """
    if record.error_code == VISITS_EXCEEDED_ERROR and not record.guards:
        return None
    trace = [guard.to_dict() for guard in record.guards]
    index = 0
    for transition in transitions:
        if transition.guard is None:
            return transition.origin if index == len(trace) else None
        step = _replay(transition.guard, trace, index)
        if step is None:
            return None
        index, passed = step
        if passed:
            return transition.origin if index == len(trace) else None
    return None


def _without_home(text: str, home: Path | None) -> str:
    if home is None:
        return text
    for form in dict.fromkeys((home.as_posix(), str(home))):
        text = text.replace(form, HOME_MARK)
    return text


def _parameters(
    state: StateReadOnlyView, input_names: set[str], values: bool, home: Path | None
) -> list[dict[str, object]]:
    parameters = []
    for entry in sorted(state.list_parameters(), key=lambda item: item["name"]):
        name = entry["name"]
        parameter: dict[str, object] = {
            "name": name,
            "codec": entry["type"],
            "source_node": entry["source_node"],
            "is_input": name in input_names,
            "value": None,
            "cut": False,
            "length": None,
        }
        if values:
            text = _without_home(render_value_as_text(state.get_param(name)), home)
            parameter.update({"value": text[:VALUE_CUT], "cut": len(text) > VALUE_CUT, "length": len(text)})
        parameters.append(parameter)
    return parameters


def _bound_input_names(journal: Sequence[dict[str, object]]) -> set[str]:
    names: set[str] = set()
    for event in journal:
        details = event.get("details")
        if event.get("code") == SessionEventCode.INPUTS_SET.value and isinstance(details, dict):
            names.update(name for name in details.get("names", []) if isinstance(name, str))
    return names


def _ending(state: StateReadOnlyView, journal: Sequence[dict[str, object]]) -> dict[str, object]:
    """How the run stands, from the outcome of its last entry: export events follow a completion (ADR 011).

    A run entered by `run` or `resume` and left with no outcome recorded was interrupted — the process
    ended mid-run — and stands where the state says, not where it was entered.
    """
    entry_codes = {SessionEventCode.WORKFLOW_STARTED.value, SessionEventCode.WORKFLOW_RESUMED.value}
    outcome_codes = {code.value for code in _OUTCOME_CODES}
    entries = [index for index, event in enumerate(journal) if event.get("code") in entry_codes]
    outcomes = [event for event in journal[entries[-1] if entries else 0 :] if event.get("code") in outcome_codes]
    status = state.get_workflow_status_code().value
    if outcomes:
        event = outcomes[-1]
        details = event.get("details")
        node_id = details.get("node_id") if isinstance(details, dict) else None
        ending: dict[str, object] = {"status": status, "event": event.get("code"), "node_id": node_id}
    else:
        ending = {"status": status, "event": journal[-1].get("code"), "node_id": state.current_node_id}
        if entries:
            ending["interrupted"] = True
    if status == "failed":
        ending["code"] = state.error_code
    return ending


def _answer_skeleton(node: WorkflowNodeModel) -> str:
    declarations = node.action_parameters.get("answer") or []
    names = [item["name"] for item in declarations if isinstance(item, dict) and isinstance(item.get("name"), str)]
    answer = {"status": "success", "text": "<answer text>", "values": dict.fromkeys(names, "<value>")}
    return json.dumps(answer, ensure_ascii=False)


def _presented(
    state: StateReadOnlyView, fields: dict[str, str], lists: dict[str, list[str]], home: Path | None
) -> tuple[dict[str, object] | None, str | None]:
    """The question as it was presented, resolved by the engine's own template rule. See ADR 016 §4.

    The paused node has not run since it presented its question, so resolving its fields against the
    state now gives the text the answerer was shown. A reference that no longer resolves leaves the
    question as written, with the reason.
    """
    try:
        presented: dict[str, object] = {
            "fields": {key: _without_home(resolve_template_text(state, text), home) for key, text in fields.items()},
            "lists": {
                key: [_without_home(resolve_template_text(state, item), home) for item in items]
                for key, items in lists.items()
            },
        }
    except WorkflowEngineError as error:
        return None, str(error)
    return presented, None


def _pending(
    state: StateReadOnlyView, workflow: WorkflowModel, ending: dict[str, object], values: bool, home: Path | None
) -> dict[str, object] | None:
    """What a paused session waits for, from the definition and, with values, as it was presented. See §3."""
    if ending["status"] != "paused":
        return None
    session = state.session_id
    resume = f"workflow-engine resume --session-id {session}"
    event = ending["event"]
    node_id = state.current_node_id
    if event == SessionEventCode.WORKFLOW_PAUSED_INTERACTIVE.value:
        node = workflow.get_node(node_id)
        if node is None or node.action_type != AskAction.ACTION_TYPE:
            return None
        written = node.action_parameters
        errors = written.get("errors")
        fields = {key: written[key] for key in _PRESENTATION_FIELDS if isinstance(written.get(key), str)}
        lists = {key: list(written[key]) for key in _PRESENTATION_LISTS if isinstance(written.get(key), list)}
        presented, presented_error = _presented(state, fields, lists, home) if values else (None, None)
        return {
            "kind": "question",
            "node_id": node_id,
            "presentation": fields,
            "lists": lists,
            "presented": presented,
            "presented_error": presented_error,
            "answer": copy.deepcopy(written.get("answer") or []),
            "errors": dict(errors) if isinstance(errors, dict) else {},
            "generic_error_code": ANSWER_FAILED,
            "resume": f"{resume} --answer '{_answer_skeleton(node)}'",
        }
    if event == SessionEventCode.WORKFLOW_PAUSED_LIMIT.value:
        return {
            "kind": "budget",
            "node_id": node_id,
            "nodes_visited": state.nodes_visited,
            "max_nodes_visited": state.max_nodes_visited,
            "resume": f"workflow-engine set-limit --session-id {session} --limit <n>\n{resume}",
        }
    if event == SessionEventCode.WORKFLOW_PAUSED_SAFETY_LIMIT.value:
        details = next((e.get("details") for e in reversed(state.get_session_events()) if e.get("code") == event), None)
        cap = details.get("hard_max_nodes_visited") if isinstance(details, dict) else None
        return {
            "kind": "safety",
            "node_id": node_id,
            "nodes_visited": state.nodes_visited,
            "hard_max_nodes_visited": cap,
            "resume": resume,
        }
    if ending.get("interrupted"):
        return {"kind": "interrupted", "node_id": node_id, "resume": resume}
    if not any(e.get("code") == SessionEventCode.WORKFLOW_STARTED.value for e in state.get_session_events()):
        return {"kind": "start", "node_id": node_id, "resume": resume}
    return None


def build_report_model(
    state: StateReadOnlyView,
    workflow: WorkflowModel,
    records: Sequence[NodeRecord],
    *,
    values: bool = True,
    home: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Build the fact model of one session from the read surfaces and the definition. See ADR 022 §2.

    ``home`` is the home directory of the machine writing the report; in the rendered values it is
    replaced by ``~``. ``values`` false leaves every value out.
    """
    journal = state.get_session_events()
    ending = _ending(state, journal)

    nodes = []
    transitions_of: dict[str, list[Transition]] = {}
    for node in workflow.nodes:
        written = dataclasses.asdict(node)
        transitions, build_error = _build(node)
        transitions_of[node.id] = transitions
        nodes.append(
            {
                "id": node.id,
                "action_type": node.action_type,
                "written": written,
                "effective": _effective(transitions),
                "build_error": build_error,
            }
        )

    path = []
    for record in records:
        entry = record.to_dict()
        entry["taken_origin"] = _taken_origin(record, transitions_of.get(record.node_id, []))
        path.append(entry)

    deliverables = set(workflow.deliverables)
    details = state.get_artifacts_detail()
    artifacts = [
        {
            "name": name,
            "path": relative,
            "description": details.get(name, {}).get("description", ""),
            "deliverable": name in deliverables,
        }
        for name, relative in sorted(state.get_artifacts().items())
    ]

    declared = {declaration.name for declaration in workflow.inputs}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": (generated_at or datetime.now(tz=UTC)).isoformat(),
        "options": {"values": values, "value_cut": VALUE_CUT, "home_replaced": values and home is not None},
        "session": {
            "id": state.session_id,
            "flow_id": state.flow_id,
            "status": ending["status"],
            "started_at": journal[0].get("timestamp") if journal else None,
            "last_event_at": journal[-1].get("timestamp") if journal else None,
            "nodes_visited": state.nodes_visited,
            "max_nodes_visited": state.max_nodes_visited,
            "ending": ending,
        },
        "definition": {
            "flow_id": workflow.flow_id,
            "start_node_id": workflow.start_node_id,
            "inputs": [declaration.to_dict() for declaration in workflow.inputs],
            "deliverables": list(workflow.deliverables),
            "nodes": nodes,
        },
        "path": path,
        "parameters": _parameters(state, declared & _bound_input_names(journal), values, home),
        "artifacts": artifacts,
        "journal": journal,
        "pending": _pending(state, workflow, ending, values, home),
    }
