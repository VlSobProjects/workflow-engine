# Architecture overview

This document describes the architecture of the project as it currently is.

It is incomplete. Only the parts settled by an accepted decision are described. The decisions that
are still open are listed at the end.

Scope rules for this document:
- Describe structure, components and their relations.
- Do not repeat the rationale, alternatives or trade-offs; those belong to the ADRs.
- Update it in the same merge that changes the architecture.

## Shape of a run

A workflow is a graph of nodes described in JSON. The engine walks it one node at a time and returns
to its caller whenever a node needs something from outside.

```
caller -> engine -> node: action -> transitions -> node ...
                     |                    |
                   state <----------------+
```

`sart_engine` is the entry point. It loads the state and the definition from a storage, builds every
node from the definition, checks that every transition target exists, and then runs until the
workflow ends, a node fails, or a node needs an exchange with the caller.

## A node

A node is **one action and an ordered list of guarded transitions**. See ADR 002.

| Part | Contract |
| --- | --- |
| Action | Performs the work and produces one `ActionNodeOutput`. An error is a value in that result. |
| Transition | A guard and a static target. The first transition whose guard holds is taken. |

An action is either automatic, and the engine continues, or interactive, and the engine returns a
`PresentResponse` to its caller and stops until it is called again with a result.

A target is one of:

- a node identifier, which is the only **routing** target,
- the end of the workflow,
- failure of the node, under a code.

If a node declares no routing target, the workflow ends after it. If it declares one and no guard
holds, the node fails. A transition whose target is the node itself, or one carrying `attempts`,
retries the node within the allowance of `max_attempts`.

## Guards

A guard is the only predicate concept. It receives the whole action result, returns a boolean, and
exposes a name identifying the rule. It never receives the state and never writes anything: the
caller passes a list of records and each guard appends its answer, which the engine then stores under
the node. The name of a guard is the error code of a node that fails it.

Guards read the state only through the parameter references the engine resolves before calling them,
so `param.` and `output.` in a guard configuration keep working.

Kinds: comparison against a value, a registered function returning a boolean, a match on the error
code, the absence of an error, and the nested groups `all_of` and `any_of`. Any guard may be negated.

The configuration key `validators` is a short form for a post-condition. When a node is built, each
entry becomes a leading transition `all_of(no_error, not P)` targeting failure under the name of `P`.
Nothing of it survives into the runtime node.

## Registries

Components are registered at import time by decorators and looked up by name from a configuration.

| Registry | Holds | Populated by |
| --- | --- | --- |
| `ACTION_REGISTRY` | Action classes by `action_type` | `@register_action` |
| `FUNCTION_REGISTRY` | Functions returning `ActionNodeOutput` | `@register_function` |
| `VALIDATOR_REGISTRY` | Functions returning `bool`, used by guards | `@register_validator` |
| `CODECS` and `CODEC_REGISTRY` | Codecs by Python type and by type name | `@register_type` |

A module that registers something has to be imported by bootstrap before workflow execution.
`ComponentLoader` loads built-in core modules first and then configured external modules.

Guards and transitions are not registries: their classes are listed in their own modules.

## State

`StateModel` carries everything a resumed run needs: the current node, counters of visits and
attempts, the output and error of each node, the guard results of the latest attempt of each node,
the parameters saved through `save_as`, and the working directory.

Values in parameters are serialized through codecs, so a parameter keeps its Python type across a
save and a load.

## Storage

`Storage` is an abstract class over a state source and a workflow source. `JsonStorage` is its only
implementation and keeps both in the working directory as `state.json` and `workflow.json`. The state
is written on every turn.

## What is not settled yet

- The exception architecture. Configuration errors escape the engine instead of becoming a response,
  and the engine still catches everything at its boundary. See ADR 001.
- The boundary between persistence and the working directory. See ADR 003.
- How data passes between nodes, and who may read or write which part of the state. The state
  currently mixes a journal written by the engine with a bus written by actions.
- The error and retry policy beyond the allowance a transition declares.
