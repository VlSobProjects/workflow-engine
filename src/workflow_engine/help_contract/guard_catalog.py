"""The static operator catalog of guard kinds. See ADR 009.

Guards are not registry-backed: their classes are listed in
``workflow_engine.transition.guards``. This catalog is the explicit source of
operator descriptions for them. Every entry is named by the configuration key an
operator writes, not by the implementing class. Besides plain guards the catalog
covers the ``reversed`` negation modifier and the ``validators`` node shorthand,
because both are part of the workflow authoring contract.
"""

from dataclasses import dataclass, field
from typing import Final

from workflow_engine.help_contract.models import HelpParameter

GUARD_KIND: Final[str] = "guard"
MODIFIER_KIND: Final[str] = "modifier"
SHORTHAND_KIND: Final[str] = "shorthand"

_DECLARED_IN_TRANSITION = "Declared inside a transition under the 'guard' or 'validator' key."
_VALUE_REFERENCES = "The value supports 'param.<name>' and 'output.<node_id>' references resolved from the state."


@dataclass(frozen=True)
class GuardCatalogEntry:
    """One operator-facing guard kind, named by its configuration key."""

    name: str
    kind: str
    summary: str
    description: str
    parameters: dict[str, HelpParameter] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


GUARD_CATALOG: Final[tuple[GuardCatalogEntry, ...]] = (
    GuardCatalogEntry(
        name="equals",
        kind=GUARD_KIND,
        summary="Holds when the output text equals the configured value.",
        description=(
            "Compares the output text of the action with the configured value and holds on exact "
            f"equality. {_VALUE_REFERENCES}"
        ),
        parameters={"equals": HelpParameter("str", "The value the output text must equal.")},
        notes=(_DECLARED_IN_TRANSITION,),
    ),
    GuardCatalogEntry(
        name="contains",
        kind=GUARD_KIND,
        summary="Holds when the output text contains the configured value.",
        description=(
            f"Holds when the configured value occurs anywhere in the output text of the action. {_VALUE_REFERENCES}"
        ),
        parameters={"contains": HelpParameter("str", "The value the output text must contain.")},
        notes=(_DECLARED_IN_TRANSITION,),
    ),
    GuardCatalogEntry(
        name="starts_with",
        kind=GUARD_KIND,
        summary="Holds when the output text starts with the configured value.",
        description=f"Holds when the output text of the action starts with the configured value. {_VALUE_REFERENCES}",
        parameters={"starts_with": HelpParameter("str", "The value the output text must start with.")},
        notes=(_DECLARED_IN_TRANSITION,),
    ),
    GuardCatalogEntry(
        name="ends_with",
        kind=GUARD_KIND,
        summary="Holds when the output text ends with the configured value.",
        description=f"Holds when the output text of the action ends with the configured value. {_VALUE_REFERENCES}",
        parameters={"ends_with": HelpParameter("str", "The value the output text must end with.")},
        notes=(_DECLARED_IN_TRANSITION,),
    ),
    GuardCatalogEntry(
        name="function_name",
        kind=GUARD_KIND,
        summary="Holds when the named registered validator function returns true.",
        description=(
            "Runs a registered validator function and holds when it returns true. The function is "
            "selected by name; its parameters are read from 'function_parameters' and support "
            "'param.<name>' and 'output.<node_id>' references. The name of the function is the "
            "error code of a node that fails this guard."
        ),
        parameters={
            "function_name": HelpParameter("str", "Name of a registered validator function."),
            "function_parameters": HelpParameter(
                "dict", "Parameters passed to the validator function.", required=False
            ),
        },
        notes=(
            _DECLARED_IN_TRANSITION,
            "The engine provides 'output' (the output text) and 'action_output' (the full action "
            "output) automatically; they are not configured.",
        ),
    ),
    GuardCatalogEntry(
        name="errors",
        kind=GUARD_KIND,
        summary="Holds when the action failed with one of the configured error codes.",
        description=(
            "Holds when the action produced an error code and that code is one of the configured "
            "list. A transition with 'errors' and no other target fails the node, keeping the error "
            "code the action produced."
        ),
        parameters={"errors": HelpParameter("list[str]", "Error codes that select this transition.")},
        notes=(
            "Declared directly on a transition; it cannot be combined with 'guard' or 'validator' "
            "in the same transition.",
        ),
    ),
    GuardCatalogEntry(
        name="no_error",
        kind=GUARD_KIND,
        summary="Holds when the action produced no error code.",
        description="Holds when the action finished without an error code.",
        parameters={
            "no_error": HelpParameter("any", "Marker key: its presence selects this guard, its value is ignored.")
        },
        notes=(_DECLARED_IN_TRANSITION,),
    ),
    GuardCatalogEntry(
        name="all_of",
        kind=GUARD_KIND,
        summary="Holds when every nested guard holds.",
        description="A group over a list of guard configurations. Holds only when all of them hold.",
        parameters={"all_of": HelpParameter("list[dict]", "Guard configurations that must all hold.")},
        notes=(_DECLARED_IN_TRANSITION,),
    ),
    GuardCatalogEntry(
        name="any_of",
        kind=GUARD_KIND,
        summary="Holds when at least one nested guard holds.",
        description="A group over a list of guard configurations. Holds when at least one of them holds.",
        parameters={"any_of": HelpParameter("list[dict]", "Guard configurations, at least one must hold.")},
        notes=(_DECLARED_IN_TRANSITION,),
    ),
    GuardCatalogEntry(
        name="reversed",
        kind=MODIFIER_KIND,
        summary="Negates the guard it is declared in.",
        description=(
            "A modifier, not a guard of its own: added to any guard configuration, it inverts the "
            "answer of that guard. The name of a negated guard is prefixed with 'not '."
        ),
        parameters={"reversed": HelpParameter("bool", "Set true to negate the enclosing guard.", required=False)},
        notes=("Valid inside any guard configuration, including nested group members.",),
    ),
    GuardCatalogEntry(
        name="validators",
        kind=SHORTHAND_KIND,
        summary="Node-level shorthand for post-conditions on the action output.",
        description=(
            "A node-level list of guard configurations checked after the action succeeds. When the "
            "node is built, each entry P becomes a leading transition all_of(no_error, not P) "
            "targeting failure under the name of P. Nothing of the shorthand survives into the "
            "runtime node."
        ),
        parameters={
            "validators": HelpParameter("list[dict]", "Guard configurations the successful output must satisfy.")
        },
        notes=("Declared on the node itself, next to 'transitions', not inside a transition.",),
    ),
)


def find_guard_entry(name: str) -> GuardCatalogEntry | None:
    for entry in GUARD_CATALOG:
        if entry.name == name:
            return entry
    return None
