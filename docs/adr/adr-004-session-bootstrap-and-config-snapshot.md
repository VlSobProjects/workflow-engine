# ADR 004: Session bootstrap and configuration snapshot

## Status
Implementing

## Active branch
`feature/adr_004-session-bootstrap-and-config-snapshot`

## Context

ADR 003 separates run bootstrapping from persistence and keeps `work_dir` in `StateModel`.
After implementation, two unresolved concerns remained:

- backend selection was coupled to engine code, because the session layer created `JsonStorage` directly;
- resume derived storage location from the current process configuration instead of session metadata.

ADR 005 partially closed the first concern: `StorageFactory` now builds storage from configuration, and
`Bootstrap` wires it before engine construction. The second concern is still open. Storage is built once,
eagerly, from the current global configuration and before any `session_id` is known, so a session started
under one storage configuration is not guaranteed to resume under the same one.

The system must support storage configuration changes over time without breaking existing sessions.

## Decision

A session records its own storage configuration, and resume uses that record instead of the current
global configuration.

- Each session stores a session metadata record in its own session directory under
  `work_dir/sessions/<session_id>/`.
- The record holds `session_id`, `work_dir`, `schema_version`, `flow_id` and the storage settings the
  session was created with.
- The storage settings in the record are written once at session creation and are never rewritten
  afterwards.
- Global configuration is the source of storage settings **only when a new session is created**.
- Resume resolves the session metadata record first and builds storage from that record.
- `Storage` is built per session, not once per process: a resumed session may use different storage
  settings than the current global configuration.
- Session metadata is authoritative for storage resolution. `StateModel` is not used to locate its own
  storage, because the state can only be read after storage is known.
- A session that cannot be resolved fails explicitly: missing record, unreadable record, or a record whose
  `session_id` does not match the requested one.

`Storage` remains a persistence contract and owns neither workspace allocation nor session metadata
resolution.

## Alternatives considered

### A. Keep global configuration as the only source of storage settings
Pros: lowest complexity; nothing new to persist.
Cons: existing sessions become unreadable after configuration drift; resume is not reproducible.
This is the state ADR 005 left behind, and it is what this ADR removes.

### B. Store the storage configuration inside `StateModel`
Pros: no new artifact; every field lives in one place.
Cons: circular dependency. Reading `StateModel` requires knowing where it is stored, so it cannot itself
carry the information needed to locate it. Rejected.

### C. Global session registry outside `work_dir`
Pros: all sessions are discoverable from any configuration; `work_dir` may change freely.
Cons: introduces a shared mutable index that needs a lifecycle, cleanup and isolation in tests, for a
benefit that is not required to make resume deterministic. Deferred to a separate ADR.

### D. Per-session metadata record inside the session directory (chosen)
Pros: no shared mutable state; the record lives and dies with the session; storage settings survive
configuration changes; resume becomes deterministic.
Cons: `work_dir` remains the discovery root, so sessions created under a different `work_dir` are not
visible until the configuration points at that `work_dir` again.

Chosen: **D**.

## Consequences

- Changing storage settings in global configuration no longer breaks already created sessions.
- Storage construction moves from process bootstrap to session resolution and becomes lazy.
- `work_dir` becomes the discovery root for sessions. This is a deliberate, recorded limitation:
  a session is found only while the configuration points at the `work_dir` it was created under.
- Cross-`work_dir` session discovery is explicitly out of scope and requires a separate ADR for a global
  session index.
- Session resolution gains explicit failure modes instead of silently falling back to current defaults.
- Existing sessions created before this decision carry no metadata record and are not resumable under the
  new contract; the implementation must fail explicitly rather than guess.

## Related ADRs

- ADR 003 persistence boundary and run workspace (Accepted): moved run start out of persistence and left
  this concern open.
- ADR 005 component loading and plugin registration model (Accepted): introduced `StorageFactory` and the
  bootstrap wiring this decision builds on.
- ADR 002 node composition (Accepted).
- ADR 001 exception architecture (Accepted).

## Implementation notes

Planned sequence:

1. Define the session metadata record and its serialized shape in the session directory.
2. Extend `StorageFactory` with two entry points:
   - build storage for a **new** session from global configuration;
   - build storage for an **existing** session from its metadata record.
3. Write the metadata record when the session directory is created, before the first state is saved.
4. Make storage resolution lazy: `Bootstrap` no longer builds a single process wide `Storage` eagerly;
   the engine resolves storage per session.
5. Normalize failures to explicit configuration/runtime errors per ADR 001.

Testing steps:

1. Resume after global storage settings changed: the session still resolves to its original storage.
2. Missing metadata record for a known `session_id`: explicit error.
3. Corrupted or unreadable metadata record: explicit error naming the session.
4. Metadata record whose `session_id` does not match the requested one: explicit error.
5. New session writes the record exactly once and does not rewrite it on later saves.
6. Existing end to end workflow start and resume still pass.

Success criteria:

- Resume never reads storage settings from the current global configuration.
- A storage settings change in configuration affects only newly created sessions.
- Every unresolvable session fails explicitly, with the session identifier in the message.

Open points:

- Whether the metadata record also stores an engine or schema compatibility marker.
- Whether a legacy session without a record gets a migration path or stays unsupported.

## Change log

- Initial draft created as a follow-up to ADR 003 implementation review.
- Reviewed against delivered ADR 005 code: `StorageFactory` exists, but resume still depends on current
  global configuration, so this ADR remains open.
- Scope reduced after architecture discussion: no global session registry and no storage profile
  identifiers. A per-session metadata record inside the session directory carries the storage settings.
- Rejected storing storage settings only in `StateModel`: the state cannot be located before storage is
  known.
- `work_dir` as the single discovery root recorded as an accepted limitation, with a global session index
  deferred to a separate ADR.
- Status changed to `Implementing`.
