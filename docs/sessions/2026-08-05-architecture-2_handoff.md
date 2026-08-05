# Session note

## Type
architecture

## Goal
Check whether ADR 005 implementation closed ADR 004, and bring ADR 004 in line with the delivered code.

## Completion criteria
- The delivered code is compared against the ADR 004 decision.
- ADR 004 either is closed as covered, or its remaining scope is restated against the code.
- ADR 004 status and the ADR registry reflect the outcome.

## Scope boundaries
- Architecture and ADR text only. No production code changes.
- No global session index design beyond recording it as deferred work.

## Status
completed

## Result
ADR 004 was not closed by ADR 005. ADR 005 delivered `StorageFactory` and bootstrap wiring, but storage is still
built once per process from the current global configuration, before any `session_id` is known, so resume is not
independent from configuration drift. ADR 004 was rewritten around a reduced scope and moved to `Implementing`.

## Decisions
- A session records its storage settings in a per-session metadata record under `work_dir/sessions/<session_id>/`.
- Global configuration supplies storage settings only when a new session is created; resume reads the record.
- Storing storage settings only in `StateModel` was rejected: the state cannot be located before storage is known.
- A global session registry outside `work_dir` was rejected for this scope and deferred to a separate ADR.
- `work_dir` stays the discovery root; this limitation is accepted and recorded in ADR 004.
- Storage construction becomes lazy and per session instead of eager in `Bootstrap`.

## Open questions
- Whether the metadata record also carries an engine or schema compatibility marker.
- Whether sessions created before this decision get a migration path or stay unsupported.

## Next steps
1. Implement ADR 004 in `feature/adr_004-session-bootstrap-and-config-snapshot`.
2. Open a follow-up draft ADR for a global session index across `work_dir` roots.
3. Open a follow-up draft ADR for entry-point discovery, still pending from the ADR 005 review.

## References
- Branch: `development`
- ADR: `docs/adr/adr-004-session-bootstrap-and-config-snapshot.md`
- Registry: `docs/adr/README.md`
