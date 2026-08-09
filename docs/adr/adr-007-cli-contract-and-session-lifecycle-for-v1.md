# ADR 007: CLI contract and session lifecycle for v1

## Status
Draft

## Active branch
—

## Context

The engine core is usable from Python API (`WorkflowEngine`) and has stable session/storage behavior,
but phase 1 target is an operator flow from command line: run a user workflow and get a result.

At the moment, there is no frozen CLI contract:

- no stable command names and arguments;
- no exit code policy;
- no output contract for automation (`json`) versus operator reading (`text`);
- no explicit lifecycle contract for `new session`, `resume`, and `set limit`.

Without this boundary, every integration chooses its own process contract and phase 1 cannot be called a
testable release.

## Decision

Define one process-level CLI contract for v1, backed by existing engine API without changing core runtime
semantics.

1. Public commands:
   - `run` — create a new session from a workflow file and execute it;
   - `resume` — continue an existing session;
   - `set-limit` — set per-session `max_nodes_visited` soft limit;
   - `show-state` — render persisted state for a session;
   - `list-sessions` — list discoverable sessions in the configured `work_dir`;
   - `help-components` — list registered actions/functions/validators/codecs and show details by name.
2. Output modes:
   - `text` (default) for operators;
   - `json` for automation (`--json` flag) with stable field names.
3. Exit codes:
   - `0`: completed successfully;
   - `2`: paused or awaiting operator action (limit/safety stop/interactive stop);
   - `3`: workflow failed by node/runtime outcome;
   - `4`: setup/config/session resolution error.
4. v1 scope excludes interactive operator input loops in the CLI. Interactive action handling remains
   phase 2.

## Alternatives considered

### A. Keep Python API only
Pros: no CLI implementation work.  
Cons: phase 1 goal ("operator runs workflow from CLI") is not met; no release boundary for integrations.

### B. Minimal single command wrapper (`run` only)
Pros: smallest implementation.  
Cons: no resumable lifecycle contract; no operator tooling for limits and diagnostics.

### C. Full lifecycle CLI contract (chosen)
Pros: testable process boundary, deterministic operator flow, suitable for scripts and CI smoke usage.  
Cost: argument design, output schema, and command-level tests.

## Consequences

- A dedicated CLI entrypoint module is required.
- Packaging must expose a stable executable command (`console_scripts`).
- Command-level tests become part of release acceptance.
- Existing Python API remains unchanged and is treated as implementation backend for CLI commands.

## Related ADRs

- ADR 004 session bootstrap and configuration snapshot (Accepted).
- ADR 005 component loading and plugin registration model (Accepted).
- ADR 006 data flow between nodes (Accepted).
- ADR 008 runtime directory and default path policy for v1 (Draft).
- ADR 009 operator help and component introspection contract (Draft).
- ADR 010 session safety cap and unbounded run policy (Draft, optional for v1).

## Implementation notes

Planned branch when status moves beyond Draft:
- `feature/adr_007-cli-contract-and-session-lifecycle-for-v1`

Implementation entrypoint target:
- `workflow_engine.cli:main` exported through `[project.scripts]`.

Minimum command acceptance for phase 1:
- run from CLI with defaults;
- run with explicit `work_dir` and `storage_dir`;
- hit limit and resume after `set-limit`;
- list available components and details by name.

## Change log

- Initial draft opened from phase 1 architecture planning session.
