# Session note

## Type
architecture

## Goal
Define phase 1 architecture scope for first CLI test release and open required ADR drafts.

## Completion criteria
- Open ADR drafts 007-009 for required phase 1 decisions.
- Open optional ADR 010 for hard safety cap policy.
- Update ADR registry with new draft rows.
- Record immediate low-cost documentation corrections and next implementation entrypoints.

## Scope boundaries
- Architecture and documentation only.
- No runtime implementation changes in this session.

## Status
completed

## Result
Opened ADR drafts 007, 008, 009, and optional 010 on `development` architecture baseline and registered
them in the ADR index. The phase 1 scope is now explicit: CLI lifecycle contract, path/default policy,
operator help contract, and optional hard safety cap policy. Immediate low-cost documentation corrections
were applied to keep architecture docs aligned with accepted ADRs.

## Decisions
- Phase 1 required decisions are split into ADR 007, 008, and 009.
- Hard safety cap policy is isolated in ADR 010 as optional for phase 1 acceptance.
- `max_nodes_visited=0` remains soft-unlimited semantics; hard cap policy (if accepted) is global config.

## Cheap improvements captured
1. Corrected architecture overview entrypoint name (`WorkflowEngine.start_workflow`).
2. Removed stale "exception architecture is not settled" note from architecture overview.
3. Updated README test instructions to root-level `pytest`.
4. Recorded `console_scripts` entrypoint as ADR 007 implementation entrypoint (`workflow_engine.cli:main`).

## Open questions
None in this session. Decision details are moved to ADR discussions.

## Next steps
1. Run dedicated architecture session for ADR 007 refinement before implementation.
2. Decide whether ADR 010 enters phase 1 mandatory scope or stays optional.

## References
- ADR registry: `docs/adr/README.md`
- ADR drafts:
  - `docs/adr/adr-007-cli-contract-and-session-lifecycle-for-v1.md`
  - `docs/adr/adr-008-runtime-directory-and-default-path-policy-for-v1.md`
  - `docs/adr/adr-009-operator-help-and-component-introspection-contract.md`
  - `docs/adr/adr-010-session-safety-cap-and-unbounded-run-policy.md`
