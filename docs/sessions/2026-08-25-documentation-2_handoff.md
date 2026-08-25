# Session 2026-08-25-documentation-2

## Type
documentation

## Goal
Record the reorder of the remaining phase 2 steps in the roadmap, so the decided order survives
the session boundary, and close the stale state of row 10.

## Completion criteria
- Row 10 states `done in 2026-08-25-implementation-6`, which delivered it.
- The pending steps stand in the decided order: the refactor debts, the notes triage, the
  live-model rehearsal of the `reorganize-folder` plan variant, the data-generation discussion
  with the generators and the drift-B protocol, the exit-scenario build.
- The roadmap preamble names this session among the reorders.

## Scope boundaries
- Only the roadmap changes: no code, no scenario documents, no notes.
- The open questions of `2026-08-25-implementation-6` stay open as decided — the `apply` variant
  is discussed in its own implementation context, expected in phase 3.

## Status
`completed`

## Result
The step table of phase 2 carries the new order and row 10 is closed. The order was decided in
conversation after the step 10 merge and would otherwise have lived nowhere.

## Decisions
1. **Debts and notes triage move ahead of the scenario work.** A refactor after the exit build
   would touch the code the gate had just validated, so the gate must run on the refactored code;
   and the notes triage is a phase-close requirement better taken off the tail. Both steps are
   bounded by existing lists — the 2026-08-23 audit and the `2026-08-23-architecture-1` triage —
   and nothing beyond them, so "prepare the code for the phase end" cannot become an open-ended
   tail.
2. **A live-model rehearsal enters as its own step.** Running the shipped `reorganize-folder`
   plan variant against a real local model exercises the whole drift-B stack — the adapter, the
   JSON binding against a model that wraps replies, the real re-ask rate of the keys guard, the
   paragraph prompt — at the cheapest possible moment, before the triage build depends on all of
   it. Prompt fixes and recorded findings are in scope; features are not.
3. **Data generation starts with a discussion session.** It is the long pole both experiments
   share (`2026-08-25-two-drifts-and-their-measurement`), the operator has proposals for it, and
   the generators step now names the discussion as its first half instead of assuming a design.

## Open questions
None of this session's own; the open questions of `2026-08-25-implementation-6` stand unchanged.

## Next steps
1. Step 11: the `refactor/` session over the 2026-08-23 audit debts.
2. Step 12: execute the notes triage.
3. Step 13: the live-model rehearsal of `reorganize-folder`.

## References
- Branch: `docs/phase-2-step-order`
- Changed: `docs/architecture/roadmap.md`
- ADRs: none
