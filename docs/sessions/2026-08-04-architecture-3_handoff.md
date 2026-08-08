# Session: Architecture backlog cleanup for missing ADR coverage

## Type
architecture

## Goal
Identify already implemented architecture behavior that is not yet covered by explicit ADRs, then prioritize the backlog.

## Completion criteria
- Current codebase is scanned for architecture-level behavior outside ADR 001-004 scope.
- Missing ADR topics are listed with priority and dependency order.
- Next architecture steps are explicit and scoped.

## Scope boundaries
Backlog analysis only. No production code changes and no ADR status changes.

## Status
completed

## Result
Backlog cleanup identified the following missing ADR topics for behavior that already exists in code or is required by accepted boundaries:

1. **Action delivery semantics and replay safety** (highest priority after ADR 004 implementation start): policy for side-effecting actions under retries/resume and failure recovery.
2. **Component loading and registration boundary**: how actions/functions/validators/codecs are discovered and loaded beyond import-time side effects.
3. **State ownership and data flow contract**: strict boundary between engine journal (`outputs`, `errors`, counters, guards) and action-owned state (`params`, `artifacts`), including read/write rules.
4. **Flow control and termination policy**: authoritative semantics for `max_nodes_visited`, `nodes_visited`, visit/attempt counters, and loop/stop guarantees.

ADR 004 remains the active architectural dependency for bootstrap and immutable session metadata; no new POC/Implementing ADR was started.

## Decisions
- Keep ADR 004 as the immediate architecture track for bootstrap/session snapshot.
- Treat backlog items above as separate one-decision ADRs; do not bundle.
- Prioritize decisions that affect runtime correctness before extensibility topics.

## Open questions
- Should delivery semantics be modeled at engine boundary only, or partially delegated to action types?
- Should registry loading support plugin modules, entry points, or explicit import manifests first?
- Which state fields are action-writable versus engine-only in the long-term model?

## Next steps
1. Prepare a narrow Draft ADR for action delivery semantics and replay/idempotency.
2. Prepare a narrow Draft ADR for component loading/discovery model.
3. Prepare a narrow Draft ADR for state ownership and data flow boundaries.
4. Revisit flow-control ADR scope after the first three drafts are reviewed.

## References
- Branch: `development`.
- Reviewed documents: `docs/architecture/overview.md`, ADR registry and ADR 001-004.
- Reviewed code areas: `engine.py`, `models/state.py`, `storage/*`, `registry/*`, `transition/*`.
