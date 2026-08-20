"""Core functions that compute on the answer an interactive node has just accepted. See ADR 015.

ADR 015 shipped the stage and no component for it: a function configured on an `ask` node is handed
the accepted answer as the injected ``output``, and until now every function that took one lived in a
test. These two are the pair the ADR-0083 scenario needed, and they are what a data-only node next to
a question used to do — surface the answered value so the node's own guards can route on it, and
accumulate it so the node that asks decides itself when the loop has enough.

Both edit the output they were given rather than building a fresh one, because the result of the
function is the whole output of the node: a function that returns something new drops the answered
values before they reach the state (ADR 015 §4).
"""

from collections.abc import Sized
from typing import Annotated

from workflow_engine.collection_param_handlers import PARAM_TYPE_MISMATCH, WriteParamMode
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, ParamWrite
from workflow_engine.registry.function_registry import register_function
from workflow_engine.tools import render_value_as_text
from workflow_engine.validators.functions_validators import not_empty_str_arg_validator

ANSWER_VALUE_MISSING = "answer_value_missing"


def _refuse(output: ActionNodeOutput, code: str, message: str) -> ActionNodeOutput:
    """Fail the node under a code while the answer keeps the values it carried.

    The writes are kept because the engine applies them before it looks at the failure, so an answer
    that was accepted lands whether the node it belongs to succeeds or fails, and a function that
    cannot compute should not be the one exception. The text goes, because it no longer describes
    what the node produced.
    """
    output.output_text = ""
    output.error_code = code
    output.error_msg = message
    return output


@register_function(
    decorators=[not_empty_str_arg_validator({"name": 0})],
    summary="Puts an answered value into the output text of the node that asked for it.",
)
def echo_answer(
    name: Annotated[str, "Name from the node's 'answer' declaration whose value becomes the output text"],
    output: Annotated[ActionNodeOutput, "The accepted answer, injected by the engine"],
    error_not_answered: Annotated[
        str, f"Error code to return when the answer carries no value under that name default '{ANSWER_VALUE_MISSING}'"
    ] = ANSWER_VALUE_MISSING,
) -> ActionNodeOutput:
    """Make a declared answer value routable by the node that asked for it.

    The counterpart of 'echo_value' for a value that has not landed yet: 'echo_value' reads the state,
    and an answered value reaches the state only after the transition has been selected, so a node
    that asks could not check what it bound without a second node in front of the guards. Configured
    on an 'ask' node, this writes the answered value into the output text and keeps every write the
    answer carried, so the node's own guards and 'validators' read it.

    The value is rendered by the one rule for text: a path in POSIX form, a list or a dict as compact
    JSON. A name the answer carries no value for is the configured error code, not empty text: an
    optional declaration left unanswered would otherwise route as if it had been answered with
    nothing.
    """
    if name not in output.param_writes:
        return _refuse(output, error_not_answered, f"The answer carries no value under '{name}'.")
    output.output_text = render_value_as_text(output.get_param(name))
    return output


@register_function(
    decorators=[not_empty_str_arg_validator({"param_name": 0})],
    summary="Appends the answer to a collection parameter and reports whether the loop has enough.",
)
def collect_answer(
    param_name: Annotated[str, "Name of the existing list, deque or set parameter the answer is appended to"],
    minimum: Annotated[int, "How many items the loop needs; supports 'param.<name>' so the bound can be flow data"],
    output: Annotated[ActionNodeOutput, "The accepted answer, injected by the engine"],
    state: Annotated[StateReadOnlyView, "Read-only state view, injected by the engine"],
    name: Annotated[str | None, "Name from the 'answer' declaration to append; the answer text when omitted"] = None,
    enough: Annotated[str, "Output text when the collection has reached the minimum default 'enough'"] = "enough",
    more: Annotated[str, "Output text while it has not default 'more'"] = "more",
    error_not_found: Annotated[
        str, "Error code to return if the collection parameter does not exist default 'param_not_found'"
    ] = "param_not_found",
    error_not_answered: Annotated[
        str,
        f"Error code to return when 'name' is declared and the answer carries no value default "
        f"'{ANSWER_VALUE_MISSING}'",
    ] = ANSWER_VALUE_MISSING,
) -> ActionNodeOutput:
    """Accumulate the answer in the node that asked for it and route the loop from there.

    Both halves of the two-node accumulating loop at once: the append that a following node used to
    make with 'append_to_param', and the size check that had to sit at the head of the loop because a
    guard sees the state as it was before its own node wrote to it. Prepare the parameter with
    'init_list_param' before the loop, configure this on the question, and route 'enough' out of the
    loop while anything else goes back to the question.

    The count is the collection as the state holds it plus the item this answer adds, so the check
    holds on the pass that reaches the minimum rather than one pass later. The APPEND write stays
    spelled out in the output, so what the node does to the collection is readable in the run.

    A parameter that does not exist is the configured error code; one that cannot be counted is
    'param_type_mismatch', the code the write itself would fail with. Either way the answered values
    still land: the node fails, the answer it accepted is not unmade.
    """
    collected = state.get_param(param_name)
    if collected is None:
        return _refuse(
            output,
            error_not_found,
            f"Parameter '{param_name}' not found in state; create it with 'init_list_param' first.",
        )
    if not isinstance(collected, Sized):
        return _refuse(
            output,
            PARAM_TYPE_MISMATCH,
            f"Parameter '{param_name}' holds {type(collected).__name__}, which cannot be collected into.",
        )
    if name is not None and name not in output.param_writes:
        return _refuse(output, error_not_answered, f"The answer carries no value under '{name}'.")
    value = output.output_text if name is None else output.get_param(name)
    output.param_writes[param_name] = ParamWrite(mode=WriteParamMode.APPEND, value=value)
    output.output_text = enough if len(collected) + 1 >= minimum else more
    return output
