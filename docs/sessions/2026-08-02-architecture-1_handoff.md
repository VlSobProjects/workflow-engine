# Session: node composition captured as an ADR

## Type
architecture

## Goal
Capture the already implemented node model as an ADR, attack it critically, and leave it in a state
that is ready to be implemented.

## Completion criteria
- The backlog of implemented but unrecorded decisions is listed in the next steps.
- One ADR covering the node model exists, is discussed and is Draft.
- The registry in `docs/adr/README.md` reflects it.

## Scope boundaries
No code changes. Defects found while reading the code are recorded as evidence in the ADR, not fixed.
The question of how data passes between nodes came up and was split off rather than decided here.

## Status
completed

## Result

ADR 002 exists as a Draft and describes what a node is: one action and an ordered list of guarded
transitions, with no validation layer at runtime.

The decision changed twice during the session, both times on evidence rather than preference.

- The model was first written as the three layers found in the code. It was then reduced to two,
  after it became clear that a validator and a transition guard are the same predicate with opposite
  defaults, and that no example configuration uses validation for branching.
- The guard result was first specified as an object carrying a declared code. That was withdrawn in
  favour of a boolean plus a name, with the caller recording the result, which carries the same
  information without rewriting any guard.

Reviewing the finished text found four further defects in the decision itself, all corrected:

- the expansion of `validators` did not fit the shape the decision claimed for a transition,
- a post-condition would have masked the real cause of a failed action,
- the rule on unmatched transitions would have failed nodes that only assert something,
- retry had no expression in the model.

## Decisions

- A node is one action and an ordered list of guarded transitions. The validation layer is removed
  from the runtime.
- A guard returns a boolean and exposes a name. It does not write; the caller records the name and
  the answer in the state. The name of the guard is the error code of a node that fails it.
- Severity belongs to the transition in the configuration, not to the guard, so guards stay reusable.
- Guards compose through nested `all_of` and `any_of`. The per-child `operator` key and its implicit
  left fold are removed.
- A transition target is a node identifier or a terminal outcome, and is always static. Computed
  targets are removed together with `TRANSACTION_REGISTRY` and `FunctionTransition`, and may be
  reintroduced by a later decision.
- The `validators` key stays in the configuration as an optional short form for a post-condition and
  is expanded when the node is built. The expansion applies only when the action did not already
  fail.
- Exactly one action per node, because one node is one exchange with the agent or the user.

## Open questions

- How data passes between nodes: the shared state or the action result. The leaning is the shared
  state. Two facts favour it: the engine returns to the caller at every interactive node, so only
  serialized data survives a turn, and `ActionNodeOutput.parameters` is not serialized; and
  `ActionParameter` already carries `source_node_id`, so provenance exists. The real question is
  therefore not which channel, but who may write, what happens on overwrite, and whether the action
  result stays as a channel within a single turn.
- Whether the record of guard results should survive a retry, rather than keeping only the latest
  attempt.
- Whether a name should be declarable in the configuration, so that two uses of the same guard
  function in one node can be told apart.

## Next steps

1. Decide how data passes between nodes, as ADR 003. It constrains ADR 002, because a guard is only
   as expressive as the result it receives.
2. Settle the boundary between ADR 001 and ADR 002: an error as a value against an error as an
   exception.
3. Take ADR 002 to Implementing in `feature/adr_002-node-composition`.
4. Capture the remaining implemented decisions, one ADR per session: the registry model and loading
   components from outside the project; automatic against interactive actions and the response
   returned to the caller; typed serialization of state parameters through codecs; the engine
   holding no memory between turns; dispatching factories by the shape of a configuration dictionary
   rather than by a type field; the error and retry model.
5. Write `docs/architecture/overview.md` once those are settled.

## References

- Branch: `docs/adr_002-node-composition`.
- ADR: [002 node composition](../adr/adr-002-node-composition.md), Draft.
- Related ADR: 001 exception architecture, Draft.
- Origin of the project: ADR 0083 in the `java-claude-ai` project, whose typed node catalogue this
  decision rejects.
