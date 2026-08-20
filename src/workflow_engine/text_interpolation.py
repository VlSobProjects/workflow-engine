"""Reference interpolation in a field declared as template text. See ADR 016.

A template field may carry ``${param.<name>}``, ``${output.<node_id>}`` and
``${artifact.<logical_name>}``; the engine replaces each with the referenced value rendered as text,
and ``$$`` writes a literal ``$``. Templating is a property of the declared field, never of strings
in general: every other configuration string keeps its exact meaning, which is what makes the
mechanism safe to add to a running system (ADR 016 §1).

The two failures live at two different times. A malformed template is a configuration error of the
node, found when the node is built and reported with every other node configuration error before the
run starts; an unresolved reference is a runtime error at presentation, raised by the same resolution
the whole-value form uses. Neither is routable: a presentation is built before its node has produced
any output, so no guard could read it (§2).
"""

from __future__ import annotations

import string

from workflow_engine.exceptions import ActionConfigurationError
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.tools import render_value_as_text

REFERENCE_PREFIXES = ("param", "output", "artifact")

_ESCAPED_DELIMITER = "$$"


class _ReferenceTemplate(string.Template):
    """``string.Template`` restricted to the braced reference form of ADR 016 §1.

    ``idpattern`` is a pattern that never matches, so ``$param.root`` without braces is not a second
    spelling of a reference but a malformed template: one syntax is read faster in review, and the
    unbraced form has no end, so ``$param.root.`` would swallow the full stop of its sentence.
    ``braceidpattern`` accepts any dotted identifier rather than only the three known prefixes, so
    that ``${HOME}`` is reported as an unknown reference prefix instead of as unreadable syntax.
    """

    idpattern = r"(?!)"
    braceidpattern = r"(?a:[_a-zA-Z][_a-zA-Z0-9]*(?:\.[-_a-zA-Z0-9.]+)?)"


def is_template_text(text: str) -> bool:
    """Tell whether the text is a template at all, which is what the delimiter announces."""
    return _ReferenceTemplate.delimiter in text


def validate_template_text(action_type: str, field_name: str, text: str) -> None:
    """Check the syntax of one template field, with no state. See ADR 016 §2.

    Called when the node is built, so a malformed template joins the configuration errors the engine
    already collects per node before the run starts (ADR 001), rather than reaching a published
    question.
    """
    if not is_template_text(text):
        return
    template = _ReferenceTemplate(text)
    if not template.is_valid():
        raise ActionConfigurationError(
            action_type,
            f"'{field_name}' is template text with a malformed placeholder: a '$' must begin either "
            f"'{_ESCAPED_DELIMITER}' for a literal '$' or a braced reference such as '${{param.name}}'",
        )
    for identifier in template.get_identifiers():
        prefix, _, name = identifier.partition(".")
        if prefix not in REFERENCE_PREFIXES or not name:
            raise ActionConfigurationError(
                action_type,
                f"'{field_name}' references '${{{identifier}}}', which is not a reference: a placeholder "
                f"names one of {', '.join(REFERENCE_PREFIXES)} followed by the name it addresses",
            )


def resolve_template_text(state: StateReadOnlyView, text: str) -> str:
    """Resolve one declared text field against the state, at presentation time. See ADR 016 §4.

    A field without the delimiter is resolved as a whole value, which is the form that predates this
    ADR and keeps working unchanged: a field that *is* a reference becomes the referenced value, any
    other string stays literal. A field that carries the delimiter is a template, and its references
    are resolved through the same call, so an unresolved one raises the error whole-value resolution
    raises today instead of passing through to the answerer as written.
    """
    if not is_template_text(text):
        return render_value_as_text(_resolve_reference(state, text))
    template = _ReferenceTemplate(text)
    values = {
        reference: render_value_as_text(_resolve_reference(state, reference))
        for reference in template.get_identifiers()
    }
    return template.substitute(values)


def _resolve_reference(state: StateReadOnlyView, value: str) -> object:
    return state.set_parameters({"value": value})["value"]
