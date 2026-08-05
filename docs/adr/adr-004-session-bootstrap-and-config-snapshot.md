# ADR 004: Session bootstrap and configuration snapshot

## Status
Draft

## Active branch
None

## Context

ADR 003 separates run bootstrapping from persistence and keeps `work_dir` in `StateModel`.
After implementation, two unresolved concerns remain:

- `WorkflowSessions` still creates `JsonStorage` directly, so backend selection is coupled to engine code.
- Resume currently derives session paths from current process configuration instead of immutable session metadata.

The system must support backend changes over time without breaking existing sessions. A session started with one
storage profile must resume with the same profile, even if global configuration changes later.

## Decision

Introduce an explicit session bootstrap layer with immutable per-session snapshot metadata:

- `StorageFactory` builds storage implementations from named global profiles.
- `SessionRegistry` stores session metadata: `session_id`, `storage_profile_id`, `work_dir`, and schema metadata.
- New session flow allocates `work_dir`, persists session metadata in registry, then creates storage through factory.
- Resume flow resolves session metadata from registry first, then recreates storage from `storage_profile_id`.

`Storage` remains a persistence contract and does not own workspace allocation or session metadata resolution.

## Alternatives considered

### A. Keep backend construction inside `WorkflowSessions`
Pros: lowest short-term complexity.
Cons: hard coupling to one backend and no safe resume when global config changes.

### B. Keep only global config and no session snapshot
Pros: simple operations model.
Cons: existing sessions can become unreadable after config drift; reproducibility is weak.

### C. Persist all workspace artifacts in storage backend
Pros: centralized data storage.
Cons: external tools still require filesystem paths; materialization complexity remains.

Chosen: **A session bootstrap layer with immutable session snapshot metadata**.

## Consequences

- Adds two new architectural components (`StorageFactory`, `SessionRegistry`).
- Introduces migration work for callers that currently construct storage directly.
- Enables backend evolution without breaking existing sessions.
- Makes resume deterministic and independent from current global defaults.
- Keeps `work_dir` as a run invariant while preserving persistence abstraction boundaries.

## Related ADRs

- ADR 003 persistence boundary and run workspace.
- ADR 002 node composition.
- ADR 001 exception architecture.

## Implementation notes

Planned sequence:

1. Define `SessionRegistry` contract and record shape.
2. Define `StorageFactory` contract and profile resolution rules.
3. Refactor `WorkflowSessions` to depend on factory + registry rather than `JsonStorage`.
4. Add tests for:
   - resume after global storage profile change;
   - failure modes when registry entry is missing or inconsistent;
   - backward compatibility strategy for existing JSON sessions.

Open points:

- Registry medium (local file, DB table, or both).
- Snapshot strictness (which fields are immutable and how mismatches are handled).
- Migration plan for already created sessions.

## Change log

- Initial draft created as a follow-up to ADR 003 implementation review.
