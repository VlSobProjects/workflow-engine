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

from workflow_engine.exceptions import (
    TransitionConfigurationError,
    WorkflowConfigurationError,
    WorkflowParameterConfigurationError,
    WorkflowParameterError,
)
from workflow_engine.tools import parameter_from_dict, parameter_from_dict_default, parameter_from_dict_optional
from workflow_engine.transition.base import (
    ATTEMPTS_KEY,
    FAIL_KEY,
    GUARD_KEY,
    NEXT_KEY,
    STOP_KEY,
    VALIDATOR_KEY,
    EndTarget,
    FailTarget,
    NodeTarget,
    Target,
    Transition,
)
from workflow_engine.transition.guards import ERRORS_KEY, BaseGuard, guard_factory


def _guard_from(data: dict[str, object]) -> BaseGuard | None:
    for key in (GUARD_KEY, VALIDATOR_KEY):
        if key in data:
            if ERRORS_KEY in data:
                raise WorkflowParameterConfigurationError(
                    message=f"A transition cannot declare both '{key}' and '{ERRORS_KEY}'"
                )
            return guard_factory(parameter_from_dict(data, key, dict))
    if ERRORS_KEY in data:
        return guard_factory({ERRORS_KEY: data[ERRORS_KEY]})
    return None


def _target_from(data: dict[str, object]) -> Target:
    node_id:str | None = parameter_from_dict_optional(data, NEXT_KEY, str)
    if node_id is not None:
        return NodeTarget(node_id=node_id)

    code:str | None = parameter_from_dict_optional(data, FAIL_KEY, str)
    if code or ERRORS_KEY in data:
        return FailTarget(code=code)

    stop:bool | None = parameter_from_dict_optional(data, STOP_KEY, bool)
    if stop:
        return EndTarget()

    if ERRORS_KEY in data:
        return FailTarget()

    raise WorkflowConfigurationError("Transition has no target")


def transition_factory(data: dict[str, object], origin: str = "transition") -> Transition:
    try:
        target = _target_from(data)
        attempts = parameter_from_dict_default(data, ATTEMPTS_KEY, bool, default_value=False)
        if attempts and not target.is_routing():
            raise TransitionConfigurationError(
                name=origin,
                parameters=data,
                message=f"'{ATTEMPTS_KEY}' needs a target that is a node, there is nothing to retry"
            )
        return Transition(target=target, guard=_guard_from(data), attempts=attempts, origin=origin)
    except (WorkflowParameterError , WorkflowParameterConfigurationError) as e:
        raise TransitionConfigurationError(
            name=origin,
            parameters=data,
            message=f"Error: {e}"
        ) from e
