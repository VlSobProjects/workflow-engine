# ADR 008: Runtime directory and default path policy for v1

## Status
Implementing

## Active branch
feature/adr_008-runtime-directory-and-default-path-policy-for-v1

## Context

Phase 1 requires a predictable operator experience when no paths are provided in CLI arguments.
Today the engine has session and storage contracts, but there is no frozen rule for how CLI defaults map
to those contracts.

Open risks without a decision:

- different callers choose different default roots;
- session discovery becomes accidental when `work_dir` drifts;
- storage paths are hard to reason about during support and diagnostics.

## Decision

For CLI v1, define deterministic default, precedence and initialization rules:

1. Runtime root and config root:
   - if neither `--work-dir` nor `--storage-dir` is provided, create/use `<cwd>/.workflow-engine/`;
   - if `--work-dir` is provided without `--storage-dir`, that value becomes the runtime root and the default work directory;
   - if `--storage-dir` is provided without `--work-dir`, the runtime root remains the default root and the storage path is overridden directly;
   - that directory is also the default location for the runtime config file.
2. Work directory:
   - `work_dir = <runtime_root>`;
   - sessions remain under `<work_dir>/sessions/<session_id>/` as ADR 004 defines.
3. JsonStorage directory:
   - default `storage_dir = <runtime_root>/json-storage/`;
   - if `--work-dir` is provided without `--storage-dir`, the default storage path becomes `<work_dir>/json-storage/`;
   - explicit `--storage-dir` overrides the JsonStorage location itself and is used as the storage root directory; no automatic `/json-storage` suffix is appended when a custom path is provided, and all storage files are created directly under that path.
4. Config discovery and precedence:
   - explicit `--config` has highest precedence for config file discovery;
   - if no explicit config is provided, search `<cwd>/.workflow-engine/workflow_engine_config.json` first and then `<user_config_dir>/.workflow-engine/workflow_engine_config.json`;
   - if no config is found, create a default config at `<runtime_root>/workflow_engine_config.json`.
5. Runtime parameter precedence:
   - explicit CLI options `--work-dir` and `--storage-dir` override the values loaded from config and environment;
   - environment variables `WE_WORK_DIR` and `WE_STORAGE_DIR` override config defaults;
   - config values are only defaults for the current process and do not get rewritten by CLI or environment overrides.
6. Path resolution:
   - relative CLI paths are resolved against the current process working directory;
   - stored paths remain serialized in POSIX form in state/session files.
7. Directory creation policy:
   - required runtime directories are created during session initialization;
   - creation failure is a configuration/setup error with the failing absolute path in the message;
   - implementation should raise `WorkflowConfigurationError` (or a dedicated subclass) so the CLI can report it consistently.

## Alternatives considered

### A. Require all paths explicitly
Pros: no hidden defaults.  
Cons: poor operator UX; phase 1 quick start is blocked by mandatory boilerplate.

### B. Use user profile config directory as default root
Pros: central storage for all runs.  
Cons: hides artifacts from project workspace; surprises users and complicates local cleanup.

### C. Default to `<cwd>/.workflow-engine` with explicit overrides (chosen)
Pros: local, visible, deterministic, aligned with session discovery model and the repository's existing `.workflow-engine` convention.  
Cost: duplicate roots across multiple project folders by design.

## Consequences

- CLI docs and help must show concrete default paths for the runtime root, work directory, storage directory and config file.
- Session discovery remains scoped to one `work_dir` root (existing limitation, not changed here).
- Operators can isolate storage/work roots deliberately through explicit options.
- Configuration resolution becomes more explicit, but implementation must preserve a predictable precedence order.

## Related ADRs

- ADR 003 persistence boundary and run workspace (Accepted).
- ADR 004 session bootstrap and configuration snapshot (Accepted).
- ADR 007 CLI contract and session lifecycle for v1 (Draft).

## Implementation notes

Planned branch when status moves beyond Draft:
- `feature/adr_008-runtime-directory-and-default-path-policy-for-v1`

Implementation clarifications:
- `--work-dir` and `--storage-dir` are process-level options and should be accepted on the shared CLI surface, not only on a subset of commands.
- config discovery should use the explicit `--config` path when present; otherwise the runtime root default is `<cwd>/.workflow-engine/` and the created config file lives at `<runtime_root>/workflow_engine_config.json`.
- failures in config lookup, config creation or directory setup should raise `WorkflowConfigurationError` so the CLI can surface them via the existing workflow error path.

Acceptance criteria for implementation stage:
- default path behavior is covered by command-level tests;
- explicit override paths are covered by tests;
- config precedence is covered by tests;
- setup failure includes the failing absolute path.

## Change log

- Initial draft opened from phase 1 architecture planning session.
- Refined the draft with explicit config precedence, `.workflow-engine` runtime root, and `WorkflowConfigurationError` semantics for setup/config failures.
- Moved the ADR to Implementing and recorded the active implementation branch.
