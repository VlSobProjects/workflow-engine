# Session: ADR 001 review, implementation gate and freeze

## Type
architecture

## Goal
Review ADR 001 implementation critically, resolve blocking architecture defects, and freeze the ADR after merge to `development`.

## Completion criteria
- Blocking defects against ADR 001 are resolved in the implementation branch.
- `feature/adr-001-exception-architecture` is merged into `development`.
- ADR 001 status and ADR registry are updated on `development` under the freeze gate.

## Scope boundaries
Only ADR 001 review outcomes, their directly related fixes, and required documentation updates for freeze.

## Status
completed

## Result

ADR 001 implementation was reviewed issue by issue and the blocking points were resolved before merge.
The branch `feature/adr-001-exception-architecture` was merged into `development`, then ADR 001
was frozen as Accepted and the ADR registry was updated accordingly.

Resolved architecture points:

- Runtime exceptions from registered functions are normalized to `FunctionRuntimeError`.
- Guard configuration no longer emits raw `TypeError` and `ValueError`.
- Configuration errors from node construction are aggregated by node id before execution.
- Global workflow node registry is reset before loading nodes, preventing cross-run leakage.
- Artifact directory creation no longer uses world-writable mode `0o777`.
- `ActionParameter` now enforces non-`None` values and codec/value compatibility.

## Decisions

- Keep configuration aggregation in setup as a collection keyed by node id.
- Keep exception-driven contracts (raise typed engine exceptions) instead of returning exception objects as values.
- Freeze ADR 001 only after merge into `development`, as required by `docs/adr/process.md`.

## Open questions

- Whether to introduce a catalog mapping error codes to stable descriptions.
- Whether configuration key validation should move to a shared schema-driven mechanism.
- Whether `state.error_code` and `state.error_msg` should be cleared on successful recovery paths.

## Next steps

1. Decide and document policy for error code cataloging.
2. Decide whether to centralize configuration key/type validation.
3. Close the remaining follow-up on state error clearing semantics.

## References

- Branch merged: `feature/adr-001-exception-architecture`.
- ADR: [001 exception architecture](../adr/adr-001-exception-architecture.md), Accepted.
