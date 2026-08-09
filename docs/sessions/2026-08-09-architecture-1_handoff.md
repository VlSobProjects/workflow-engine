# Session note

## Type
architecture

## Goal
Run ADR 006 final acceptance, close remaining architecture questions, and freeze the ADR if the freeze gate is satisfied.

## Completion criteria
- Resolve all open ADR 006 architecture questions.
- Confirm implementation and tests match ADR 006.
- Merge `feature/adr_006-data-flow-between-nodes` into `development`.
- Set ADR 006 to `Accepted` and update the ADR registry.

## Scope boundaries
- ADR 006 acceptance and tightly coupled documentation synchronization only.
- No unrelated architecture or feature work.

## Status
completed

## Result
ADR 006 passed acceptance and is now frozen as `Accepted`. The open question from implementation handoff
was resolved by extending the event contract with `workflow_setup_failed` and implementing it at the
engine boundary for setup/build validation failures. The branch `feature/adr_006-data-flow-between-nodes`
was merged into `development`, ADR status was updated, and registries were synchronized.

## Decisions
- Setup/build validation failures are recorded as `workflow_setup_failed` engine events to keep the
  "every external engine call is auditable" contract true.
- ADR 006 is accepted and frozen with the delivered event contract, including setup-failure journaling.

## Open questions
None.

## Next steps
1. Optionally tighten `set_session_limits` validation against `nodes_visited` to reject already-exceeded limits.

## References
- ADR: `docs/adr/adr-006-data-flow-between-nodes.md`
- Merged branch: `feature/adr_006-data-flow-between-nodes`
- Target branch: `development`
