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

Delivered in `feature/adr_004-session-bootstrap-and-config-snapshot`:

1. `WorkflowSession` is the session metadata record. It is serialized as `session.json` inside the session
   directory and holds `session_id`, `work_dir`, `flow_id`, `schema_version`, `timestamp` and the storage
   settings of the session.
2. `WorkflowSessionsFactory` writes the record when the session is created and loads it on resume.
   Loading validates the record before any state is read: it must be readable, must sit in the directory it
   describes, and must carry the requested `session_id`.
3. `StorageFactory` was split into two responsibilities: producing the storage settings for a new session
   from global configuration, and building a `Storage` from the settings of a given session.
4. `Bootstrap` no longer builds a process wide `Storage`. It passes `StorageFactory` to the engine, which
   resolves storage per session.
5. `WorkflowEngine` builds storage from the record on resume and from configuration on a new session, and
   rejects a session whose record and state disagree.
6. Failures of session resolution are raised as `WorkflowRuntimeError`, including corrupted records and
   filesystem failures, so nothing raw escapes the boundary. See ADR 001.

Paths are serialized in POSIX form. Without it the same session directory is written differently depending
on the shell the engine runs from, which makes the recorded paths compare unequal and forces conversion at
every call site.

Tests delivered in `tests/test_engine.py`:

1. Resume under a changed global storage configuration keeps the storage of the session, and the storage
   directory the current configuration points at is never created.
2. The session record is written once and is byte identical after a later resume.
3. A missing record fails and names the session.
4. A corrupted record fails as an engine error, not as a raw decoding failure.
5. A record carrying another `session_id` fails before the state is looked up, naming both identifiers.

Success criteria, as verified:

- Resume never reads storage settings from the current global configuration.
- A storage settings change in configuration affects only newly created sessions.
- Every unresolvable session fails explicitly, with the session identifier in the message.

Resolved open points:

- The record carries no engine or schema compatibility marker beyond `schema_version`.
- Sessions created before this decision are not supported and fail as unresolvable; there are no such
  sessions outside development workspaces.

Left open on purpose:

- The storage settings are a plain mapping with no backend discriminator, because `JsonStorage` is still
  the only implementation. Introducing a second backend requires deciding how the record identifies it.
- Discovery across several `work_dir` roots.

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
- Implementation notes rewritten to describe the delivered result, including POSIX path serialization and
  the validation rules of the session record.
- Freeze gate passed after merge into `development`; status changed to `Accepted`.
