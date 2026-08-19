# Session note

## Type
implementation

## Goal
Close the one mechanical gap between the engine and the ADR-0083 `FQ` scenario: a loop that collects
an answer on every pass and leaves once it has collected enough.

## Completion criteria
1. A core function appends one value to an existing collection parameter, next to `init_list_param`.
2. A bounded accumulating loop is expressible with core components only, and is proven end to end
   through the CLI, not only at the unit level.
3. `pytest` and `ruff` pass from the command line.
4. The coverage note — the yardstick for the first goal of phase 2 — records the result and whatever
   building it taught.

## Scope boundaries
- No change to write semantics, to the counters, or to when the engine applies a write. The bound is
  built from what the loop collected, not by changing what `attempts` means.
- The full ADR-0083 scenario is not built here; this session delivers the piece it was missing.
- The `S` node type (a script-running function) stays out: it is a trust decision of its own.

## Status
completed

## Result
All four criteria are met. Two small components, one capability:

- `append_to_param` (`actions/modify_param_functions.py`) — appends one value to an existing list,
  deque or set parameter; a missing parameter is a configurable error code, the way
  `set_param_from_deque` already reports one, and a parameter that cannot be appended to fails the
  write with `param_type_mismatch` from the path that owns that knowledge.
- `is_collection_size_at_least` (`validators/output_function_validators.py`) — the counting half. A
  function guard's arguments are resolved from the state, so `param.answers` arrives as the list
  itself; reversed, the same guard is the transition that keeps the loop going.

Verified from the command line: `uv run ruff check .` clean, `uv run pytest` 364 passed (355 before).
`tests/test_bounded_accumulating_loop.py` drives the whole loop through the CLI — three answers, three
passes, exit on the third — and `tests/test_modify_param_functions.py` covers the function itself.

## Decisions
1. **Two components, not a change of semantics.** The alternative was to make `attempts` survive a
   loop that leaves the node, or to add a guard over `visit_counters`. Both change what a counter
   means for every workflow; counting what was collected changes nothing and reads better in the
   definition, because the exit condition is the thing the loop is actually for.
2. **`append_to_param`, not `append_to_list_param`.** The `APPEND` mode is implemented for lists,
   deques and sets alike, so the name that promises only lists would be the narrow one.
3. **The function checks existence, the write path checks the type.** Duplicating the collection
   table inside the function would put the same knowledge in two places; the missing-parameter case is
   worth catching early only because the write path's message for it says nothing about the fix.

## Open questions
Two ordering properties of `StateModel.update` surfaced while building the loop. The first is now
documented; the second is not resolved.

1. **A guard sees the state as it was before its own node wrote to it.** The engine selects the
   transition first and applies the node's writes when the step is taken, so the size check cannot sit
   on the node that appends. This is not a defect — the guard reads the action result, which it is
   given directly — but it was written down nowhere, and it decides the shape of every accumulating
   loop. Now stated in the guards section of the architecture overview.
2. **A failing parameter write cannot influence routing.** Because the transition is chosen first, a
   write that fails afterwards (`param_overwrite_forbidden`, `param_type_mismatch`) records an error
   on the node and sets the output's error code, but the run has already taken the transition selected
   for a successful output. ADR 006 treats a write error as a node error, so this deserves a decision:
   either the writes are applied before the transition is selected, or the failure is routed on the
   following node. Not touched here — it changes execution order for every node.

## Next steps
1. Build the ADR-0083 scenario as one workflow and run it, by a scripted end-to-end test and by a live
   agent — the check itself, and the second item of the coverage note's list.
2. Decide text interpolation with the evidence that step produces.
3. Open the question above about a failing write and routing.

## References
- Note updated: `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` (the `FQ` row, the
  re-verification section, and the first item of the remaining list)
- Branch: `feature/bounded-accumulating-loop`
- Previous session: `2026-08-19-implementation-14_handoff.md`
- Touches: ADR 002 (guards and transitions), ADR 006 (the bus and write modes), ADR 009 (the new
  components carry their operator documentation), ADR 013 (the answer this loop collects)
