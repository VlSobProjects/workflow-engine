# Session note

## Type
architecture

## Goal
Re-run ADR-007 acceptance, align the ADR text with the delivered CLI contract, and freeze the decision if the gate is satisfied.

## Completion criteria
1. Confirm the implemented CLI surface against ADR-007.
2. Resolve any contract mismatch that blocks acceptance.
3. Merge the feature branch to `development`.
4. Update ADR-007 status and the ADR registry on `development`.
5. Close the session note with the outcome and next steps.

## Scope boundaries
- ADR-007 text and the tightly coupled ADR registry entry.
- No runtime CLI refactor unless it is required to remove a blocking mismatch.
- No new ADR creation.

## Status
completed

## Result
ADR-007 was accepted after the feature branch was merged to `development`. The public CLI contract now matches the delivered surface, including `help-component` as the detail command and the installed `workflow-engine` entry point as the acceptance path.

## Decisions
1. Keep `help-component` as a public v1 command.
2. Treat the installed `workflow-engine` console script as the process-level acceptance target.
3. Freeze ADR-007 as `Accepted` on `development` and update the registry in the same change.

## Open questions
None.

## Next steps
1. Proceed with ADR-008, ADR-009, and ADR-010 as separate architecture work.

## References
- ADR: `docs/adr/adr-007-cli-contract-and-session-lifecycle-for-v1.md`
- Branch: `feature/adr_007-cli-contract-and-session-lifecycle-for-v1` (merged)
- Preceding session: `2026-08-11-architecture-1_handoff.md`
