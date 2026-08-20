"""How a component calls a registered function: the injection convention, in one place. See ADR 015 §3a.

Beside its own resolved ``function_parameters``, a registered function receives arguments it did not
configure. Which ones depends on what calls it, and the difference is deliberate rather than
accidental:

- An **action** runs a function returning an ``ActionNodeOutput``. It is given ``state``, the
  read-only view, and ``output``, the ``ActionNodeOutput`` the node received: the previous node's
  output for an automatic action, the accepted answer for an interactive one.
- A **guard** runs a validator returning a boolean. It is given ``output``, which here is the output
  *text*, and ``action_output``, the object. It is never given the state: a guard reads the state
  only through the references the engine resolved into its configuration (ADR 002).

Both conventions live here so that the difference between them is read rather than remembered, and
so that a new caller adds no fourth copy of either.
"""

from __future__ import annotations

from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import RegisteredFunctionExecutor


def run_action_function(
    executor: RegisteredFunctionExecutor[ActionNodeOutput],
    state: StateReadOnlyView,
    output: ActionNodeOutput | None,
) -> ActionNodeOutput:
    """Run the registered function of an action with the standard injection."""
    return executor.execute(parameters_modified=state.set_parameters_with_updater({"output": output, "state": state}))


def run_guard_function(
    executor: RegisteredFunctionExecutor[bool],
    state: StateReadOnlyView,
    output: ActionNodeOutput,
) -> bool:
    """Run the registered validator of a guard with the injection a guard gets."""
    return executor.execute(
        parameters_modified=state.set_parameters_with_updater({"output": output.output_text, "action_output": output})
    )
