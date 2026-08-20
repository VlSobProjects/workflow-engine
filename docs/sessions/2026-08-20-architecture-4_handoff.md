# Session note

## Type
architecture

## Goal
Decide the per-node visit cap with the evidence the ADR-0083 flow produced — a retry that re-enters a
question as a fresh visit is bounded by nothing but the global hard cap — together with the counters
question ADR 015's Consequences carry, and open it as an ADR if it is worth deciding.

## Completion criteria
1. The question is argued in critical mode: at least two alternatives, the trade-offs named, the cost
   stated.
2. If it is worth deciding, the ADR exists as `Draft` with its registry row, scoped to what the
   evidence supports.
3. The hard-node-cap scoping note is updated: the per-node dimension points at the decision; the
   global-cap scope question keeps its own status on its own merits.
4. The counters question from ADR 015's Consequences ("either the counters stop resetting or the
   event carries the attempt") is answered or explicitly kept open with the fork stated.

## Scope boundaries
- No engine code.
- ADR 010 stays Accepted and unedited; if the decision is additive it does not supersede it, and this
  session states which it is.
- The global cap's scope (host vs workflow vs workflow type) is not decided here unless the per-node
  decision forces it.
- ADR 015 and ADR 016 texts are not edited except where a decision here resolves a pointer they
  carry.

## Status
completed

## Result
ADR 017 "Per-node visit cap" is open as `Draft` on `development`, registered, with no open points —
small enough to implement directly when its turn comes. Six alternatives are recorded. The
cap-scoping note carries the decided per-node dimension and keeps its global question open with the
stakes honestly lowered; ADR 015's Consequences pointer is resolved to ADR 017 with a change log
entry. All four completion criteria are met.

## Decisions
All in ADR 017; argued in its text, the shape fixed by a boundary stated before the mechanism.
1. **A business bound is not a safety bound** — the framing that decided the shape. How many
   follow-ups a task needs is dynamic and already expressible in flow data: the bound value is a
   parameter (set by an answer, a function or an input), guards resolve `param.` references, and
   with ADR 015 the asking node accumulates and routes on "enough" itself. The cap is the declared
   static ceiling that holds when that logic is wrong; making it dynamic would let broken logic
   raise its own bound.
2. **Declared `max_visits` on the node, enforced by the engine on entry**, failing the workflow
   under `max_visits_exceeded` before the action runs — symmetric to `max_attempts` /
   `max_attempts_exceeded` in declaration place and failure mode; the counter half
   (`visit_counters`) already existed unread.
3. **No default**: any number right for an interactive loop is false for a scan, and a
   routinely-silenced safety default is worse than an opt-in. Undeclared nodes keep the ADR 010
   backstop.
4. **Not routable**: the entry check precedes the action, so there is no output for guards; the
   in-graph continue/summarize/finish fork on exhaustion belongs to the budget-checkpoint family
   (ADR 010), deliberately not smuggled in.
5. **The counters keep resetting; the journal gains ordinals**: `interactive_answered` carries the
   visit number and the attempt-within-visit ordinal, settling ADR 015's cost line — enforcement
   state and audit surface separated cleanly.
6. **Counters-as-parameters rejected** (alternative F): writable safety state would make the cap
   advisory, a visit is not a question semantically, and the universality it aimed at comes from
   the bound being a parameter instead. Read-only counter exposure to guards recorded as considered
   and not taken.

## Open questions
None new. The global cap's scope stays open in the cap-scoping note; the in-graph exhaustion
checkpoint stays with ADR 010's territory.

## Next steps
1. Open `feature/adr_015-computation-inside-an-interactive-node`, move ADR 015 to Implementing, and
   implement it — the post-function keys on `ask`, the shared injection runner, the accessor-pair
   decision.
2. ADR 016 and ADR 017 follow as their turns come: 016 has two small open points to settle at or
   before implementation, 017 has none. Rule 11 allows only one ADR in Implementing at a time.
3. The remaining queue beyond these: prompt-templating implementation unblocks reconsidering
   ADR 015's pre-processing deferral; ADR 014 resumes with its open point 1 already decided; the
   re-presentation wording question (ADR 013 §6) still wants its own decision.

## References
- Branch: `development`
- ADR opened: `docs/adr/adr-017-per-node-visit-cap.md`
- Updated: `docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md`,
  `docs/adr/adr-015-computation-inside-an-interactive-node.md` (Consequences pointer + change log),
  `docs/adr/README.md`
- Evidence: `docs/sessions/2026-08-20-investigation-1_handoff.md`, `tests/test_adr0083_scenario.py`
- Related: ADR 002, ADR 010, ADR 013, ADR 015
- Previous session: `2026-08-20-architecture-3_handoff.md`
