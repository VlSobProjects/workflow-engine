# ADR 008: Runtime directory and default path policy for v1

## Status
Draft

## Active branch
—

## Context

Phase 1 requires a predictable operator experience when no paths are provided in CLI arguments.
Today the engine has session and storage contracts, but there is no frozen rule for how CLI defaults map
to those contracts.

Open risks without a decision:

- different callers choose different default roots;
- session discovery becomes accidental when `work_dir` drifts;
- storage paths are hard to reason about during support and diagnostics.

## Decision

For CLI v1, define deterministic default and override rules:

1. Runtime root:
   - if neither `--work-dir` nor `--storage-dir` is provided, create/use `<cwd>/workflow-engine/`.
2. Work directory:
   - `work_dir = <runtime_root>`;
   - sessions remain under `<work_dir>/sessions/<session_id>/` as ADR 004 defines.
3. JsonStorage directory:
   - default `storage_dir = <runtime_root>/json-storage/`;
   - explicit `--storage-dir` overrides only storage location.
4. Path resolution:
   - relative CLI paths are resolved against current process working directory;
   - stored paths remain serialized in POSIX form in state/session files.
5. Directory creation policy:
   - required roots are created eagerly at command start;
   - creation failure is a setup error with explicit path in message.

## Alternatives considered

### A. Require all paths explicitly
Pros: no hidden defaults.  
Cons: poor operator UX; phase 1 quick start is blocked by mandatory boilerplate.

### B. Use user profile config directory as default root
Pros: central storage for all runs.  
Cons: hides artifacts from project workspace; surprises users and complicates local cleanup.

### C. Default to `<cwd>/workflow-engine` with explicit overrides (chosen)
Pros: local, visible, deterministic, aligned with session discovery model.  
Cost: duplicate roots across multiple project folders by design.

## Consequences

- CLI docs and help must show concrete default paths.
- Session discovery remains scoped to one `work_dir` root (existing limitation, not changed here).
- Operators can isolate storage/work roots deliberately through explicit flags.

## Related ADRs

- ADR 003 persistence boundary and run workspace (Accepted).
- ADR 004 session bootstrap and configuration snapshot (Accepted).
- ADR 007 CLI contract and session lifecycle for v1 (Draft).

## Implementation notes

Planned branch when status moves beyond Draft:
- `feature/adr_008-runtime-directory-and-default-path-policy-for-v1`

Acceptance criteria for implementation stage:
- default path behavior is covered by command-level tests;
- explicit override paths are covered by tests;
- setup failure includes the failing absolute path.

## Change log

- Initial draft opened from phase 1 architecture planning session.
