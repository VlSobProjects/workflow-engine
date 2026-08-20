# Session note

## Type
implementation

## Goal
Implement ADR 017: a node may declare `max_visits`, the engine enforces it on entry and fails the
workflow under `max_visits_exceeded`, and `interactive_answered` gains the visit and attempt ordinals.

## Completion criteria
1. A node may declare `max_visits`; a node without it stays unbounded, and a declared value below `1`
   is refused as a configuration error (§1, §2, with the value rule settled in this session).
2. The engine checks the cap when it is about to run the node, before the action, so a question beyond
   the cap is never asked; the run fails under `max_visits_exceeded` naming the node, and the failure
   is not routable by the capped node's transitions (§1, §3).
3. A plain `resume` that re-presents a question consumes no visit and therefore does not move the cap
   (ADR 013 §6).
4. `interactive_answered` carries the visit number and the attempt ordinal within the visit, and the
   counters keep their current reset semantics (§4).
5. The unbounded retry of `tests/test_adr0083_scenario.py` becomes the bounded case: the same wrong
   answer ends in `max_visits_exceeded` at the question node.
6. `uv run pytest` and `uv run ruff check .` pass, with new tests covering the behaviour.
7. `README.md` and `docs/architecture/overview.md` carry the change.

## Scope boundaries
- No default value for `max_visits`, and no change to the ADR 010 caps.
- The counters keep resetting on departure: `max_attempts` stays a per-visit bound.
- No in-graph exhaustion checkpoint (continue / summarize / finish) — that is the budget-checkpoint
  family of ADR 010, not this decision.
- No read-only exposure of the engine counters to guards.
- No new node-key section in the ADR 009 help contract: `max_visits` is documented where
  `max_attempts` already is, and the ADR's Consequences line is corrected to say so.
- The ADR-0083 coverage note is not re-measured here; that is its own session.

## Status
completed

## Result
ADR 017 is implemented. A node may declare `max_visits`; the engine refuses to enter a node that has
completed that many visits and fails the workflow under `max_visits_exceeded` before the action runs,
so a question beyond the cap is never published. The exhaustion is not routable, a node without the
key stays unbounded, a declared value below `1` is a configuration error, and a re-presented question
still consumes nothing. `interactive_answered` now carries the `visit` and `attempt` ordinals.

All seven completion criteria are met: `uv run ruff check .` is clean, `uv run ruff format --check .`
reports 250 files formatted, and `uv run pytest` reports 424 passed, 8 of them new.

The gap the ADR was opened for is closed where it was measured: the ADR-0083 flow's unbounded retry
now ends at the question node with `max_visits_exceeded` instead of running to the global cap.

## Decisions
1. **The entry check sits at the action dispatch, not at the top of the run loop.** An iteration of
   the loop begins with `cur_node` still holding the node whose output is being routed; the node about
   to run is known only after the transition has been taken. Checking at the top would test the node
   being left. Recorded in the ADR's Implementation notes.
2. **A node that never ran records its error directly.** There is no `ActionNodeOutput` to carry it,
   and the normal write path would count a visit the node never made. `StateModel.record_node_error`
   was added for it and `_update_cur_node` now shares it, so the error string keeps one format.
   Recorded in the ADR.
3. **A declared `max_visits` below `1` is refused as a configuration error** (asked and settled with
   the user). Absence of the key stays the only spelling of "unbounded"; `0` is not a second one. The
   ADR 010 `max_nodes_visited`, where `0` does mean "no soft limit", is an operator setting on a
   session rather than a statement an author writes into a definition. §2 of the ADR was amended.
4. **`max_visits` is not published through the ADR 009 help contract** (asked and settled with the
   user). That contract is per component and publishes no node keys at all — `max_attempts` appears
   in it only as a transition hint of `ask` — so `max_visits` is documented the same way, plus
   `README.md` and the overview. A node-key help surface would change a stable contract and is its own
   decision. The ADR's Consequences were corrected to say so instead of claiming an ADR 009 cost.
5. **The ADR-0083 scenario declares `max_visits: 3` on its first question.** The ADR's Implementation
   notes prescribed turning the flow's unbounded-retry test into the bounded case; the value is an
   order beyond the single visit the happy paths make, which is the authoring rule of §5 applied to
   the flow that produced the evidence.

## Open questions
None from the implementation. One fact is recorded rather than acted on: `max_attempts` is still
undocumented as a node key on any machine-readable surface, and `max_visits` now joins it. Whether
node keys deserve a help surface of their own is left open in the ADR's Consequences.

## Next steps
1. Merge into `development` and set ADR 017 to `Accepted` through the freeze gate.
2. Re-measure `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` against ADR 015,
   ADR 016 and ADR 017 together: the `attempt_counters`/`max_visits` row of the mapping table and
   friction 1 are now answered, and "What building it found" items 1 and 2 have changed. The note's
   own next step — whether the flow's questions and the two shipped `ask` templates should be
   rewritten to carry their values inside the sentence — belongs to the same pass.
3. ADR 014 as its turn comes; its open point 1 is decided for the in-text case by ADR 016.

## References
- Branch: `feature/adr_017-per-node-visit-cap`
- ADR: `docs/adr/adr-017-per-node-visit-cap.md`
- Added: `tests/test_adr017_max_visits.py`
- Changed: `src/workflow_engine/engine.py`, `models/node.py`, `models/state.py`,
  `actions/action_ask.py`, `tests/test_adr0083_scenario.py`, `tests/test_adr013_e2e_interactive.py`,
  `README.md`, `docs/architecture/overview.md`
- Previous session: `2026-08-20-implementation-2_handoff.md`
