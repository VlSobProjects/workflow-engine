# Session note

## Type
implementation

## Goal
Record a written parameter as produced by the node that produced it, instead of by the node the run
moved on to.

## Completion criteria
1. `ActionParameter.source_node_id` of a value written through `param_writes` names the producing
   node, both at the state level and end to end through the engine.
2. The producing node is passed to the write explicitly, so the correctness no longer depends on when
   `current_node_id` happens to move.
3. `pytest` and `ruff` pass from the command line, with tests that fail on the old order.

## Scope boundaries
- No change to what `source_node_id` means for an operator-bound input: it keeps recording the node
  the session starts at, which is what it recorded before. See the open question.
- No change to counters, routing, or the shape of the persisted state.
- Nothing reads `source_node_id`, so this fixes provenance, not behaviour.

## Status
completed

## Result
All three criteria are met. `StateModel.update` applies the parameter writes before `_update_stats`,
and both `_param_write` and `_set_artifacts` take the producing node as an argument instead of
reading `current_node_id`. Four state-level tests and one end-to-end assertion in the ADR 013 suite
cover it; all of them fail on the old order.

Verified from the command line: `uv run ruff check .` clean, `uv run pytest` 342 passed.

The defect: `update` did `_update_cur_node`, then `_update_stats` — which sets
`current_node_id = next_node_id` — and only then applied `param_writes`, which created each new
`ActionParameter` with `self.current_node_id`. So a value produced by node A was recorded as produced
by node B. It stayed invisible because nothing reads the field, and because it is correct whenever
the run ends (no next node) or the node loops back to itself. The clearest symptom was one node
disagreeing with itself: `save_as` is written in `_update_cur_node`, before the move, so the same
node's output text and its parameter writes carried different producers.

`_set_artifacts` had the same defect for `artifact_overwritten` and `artifact_path_conflict` events,
which are attributed the same way, and is fixed in the same pass.

## Decisions
1. **The producer is an argument, not state.** Reordering alone would fix today's symptom and leave
   the trap: the write is applied while the run is between two nodes, so reading a "current" node is
   the wrong question to ask. `_param_write(name, write, source_node_id)` states what it records.
2. **An existing parameter keeps the node that created it.** A write to a name already on the bus
   changes the value only, which is what `_param_write` already did; the field answers "who created
   this name", not "who wrote it last". Documented in the method rather than changed: making it
   "last writer" is a different decision, and nothing needs it yet.
3. **The artifact events are fixed with it.** Same method, same cause, same one-line shape; leaving
   them attributed to the next node would have meant fixing half a defect.

## Open questions
What `source_node_id` should be for a value the operator bound with `set-input`. Today, and after
this fix, it is the node the session starts at — a node that never ran and did not produce the value.
Something like an explicit non-node marker would be more truthful, but it changes what a persisted
state carries for every session with inputs, and nothing reads the field yet, so it is not worth a
migration on its own. Worth folding into whatever decision first gives the field a reader.

## Next steps
1. Decide the value-rendering question left by the previous session: `ValueGuard.converted_value` and
   `echo_value` render a value with `str()`, so a `Path` compared or emitted on Windows carries native
   separators against ADR 008. It changes guard behaviour, so it needs its own branch and tests.
2. The remaining items of the ADR 013 review
   (`docs/architecture/notes/2026-08-19-interactive-exchange-publishing-boundary.md`).
3. The atomic `state.json` write, still open from the recovery roadmap note (c).

## References
- Branch: `fix/param-write-provenance`
- Previous sessions: `2026-08-19-implementation-11_handoff.md` (found it while building the ADR 013
  example), `2026-08-19-implementation-12_handoff.md`
- Touches: ADR 006 (the bus and what the state records about a write), ADR 011 (artifact events)
