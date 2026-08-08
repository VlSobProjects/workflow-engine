# Session note

## Type
architecture

## Goal
Refine ADR 006 with an operator control/audit contract for stop-limit override and resume handling.

## Completion criteria
- ADR 006 defines an explicit operator event journal contract.
- ADR 006 defines the requirement that external engine calls are recorded as operator events.
- ADR 006 change log records this architecture amendment.

## Scope boundaries
- ADR text refinement only.
- No production code edits in this session.

## Status
completed

## Result
ADR 006 now includes an explicit `state.operator_events` contract for operator-level auditability.
The decision requires recording all external engine calls as structured operator events, including
session creation, start, stop by guardrail, limit override, resume, completion, and failure outcomes.

## Decisions
- Introduce a dedicated operator event journal in state, separate from business parameters.
- Treat all external engine API calls as auditable events with a normalized event shape.
- Keep this as an ADR-level contract; implementation details remain in implementation work.

## Open questions
None.

## Next steps
1. Implement operator event persistence and serialization in `StateModel`.
2. Add an engine-level API to update session limits (for example `max_nodes_visited`) with explicit audit events.
3. Add an e2e resume-equivalence test: stop on limit, increase limit, resume, compare with straight run.

## References
- ADR: `docs/adr/adr-006-data-flow-between-nodes.md`
