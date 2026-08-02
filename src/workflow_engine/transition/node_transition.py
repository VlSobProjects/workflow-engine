"""Building transitions from configuration.

Recognised forms:

- ``{"next": "NODE_2"}`` — always go to a node.
- ``{"next": "NODE_2", "validator": {...}}`` — go there when the guard holds.
- ``{"next": "NODE_2", "errors": [...], "attempts": true}`` — go there when the action failed with
  one of the codes; with ``attempts`` the node is retried first.
- ``{"errors": [...]}`` — fail the node, keeping the error code the action produced.
- ``{"errors": [...], "fail": "code"}`` — fail the node under a code of its own.
- ``{"stop": true}`` — end the workflow.

``attempts`` is only meaningful for a target that is a node, because there is nothing to retry before
ending or failing. See ADR 002.
"""

from __future__ import annotations

from workflow_engine.exceptions import WorkflowError
from workflow_engine.transition.base import EndTarget, FailTarget, NodeTarget, Target, Transition
from workflow_engine.transition.guards import ERRORS_KEY, BaseGuard, guard_factory

NEXT_KEY = "next"
VALIDATOR_KEY = "validator"
GUARD_KEY = "guard"
ATTEMPTS_KEY = "attempts"
STOP_KEY = "stop"
FAIL_KEY = "fail"


def _guard_from(data: dict[str, object]) -> BaseGuard | None:
    for key in (GUARD_KEY, VALIDATOR_KEY):
        if key in data:
            if ERRORS_KEY in data:
                raise WorkflowError(f"A transition cannot declare both '{key}' and '{ERRORS_KEY}': {data}")
            guard_data = data[key]
            if not isinstance(guard_data, dict):
                raise TypeError(f"Expected '{key}' to be a dictionary, got '{type(guard_data).__name__}'")
            return guard_factory(guard_data)
    if ERRORS_KEY in data:
        return guard_factory({ERRORS_KEY: data[ERRORS_KEY]})
    return None


def _target_from(data: dict[str, object]) -> Target:
    if NEXT_KEY in data:
        node_id = data[NEXT_KEY]
        if not isinstance(node_id, str):
            raise TypeError(f"Expected '{NEXT_KEY}' to be a string, got '{type(node_id).__name__}'")
        return NodeTarget(node_id=node_id)
    if FAIL_KEY in data:
        code = data[FAIL_KEY]
        if not isinstance(code, str):
            raise TypeError(f"Expected '{FAIL_KEY}' to be a string, got '{type(code).__name__}'")
        return FailTarget(code=code)
    stop = data.get(STOP_KEY)
    if stop is not None:
        if not isinstance(stop, bool):
            raise TypeError(f"Expected '{STOP_KEY}' to be a bool, got '{type(stop).__name__}'")
        if stop:
            return EndTarget()
    if ERRORS_KEY in data:
        return FailTarget()
    raise WorkflowError(f"Transition has no target: {data}")


def _attempts_from(data: dict[str, object]) -> bool:
    value = data.get(ATTEMPTS_KEY, False)
    if not isinstance(value, bool):
        raise TypeError(f"Expected '{ATTEMPTS_KEY}' to be a bool, got '{type(value).__name__}'")
    return value


def transition_factory(data: dict[str, object], origin: str = "transition") -> Transition:
    target = _target_from(data)
    attempts = _attempts_from(data)
    if attempts and not target.is_routing():
        raise WorkflowError(f"'{ATTEMPTS_KEY}' needs a target that is a node, there is nothing to retry: {data}")
    return Transition(target=target, guard=_guard_from(data), attempts=attempts, origin=origin)
