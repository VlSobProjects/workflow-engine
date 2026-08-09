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
5. CLI framework:
   - use `argparse` from the Python standard library in v1;
   - add no new runtime dependency for command parsing;
   - keep parser logic thin and isolated from command behavior.
6. Layered CLI design:
   - transport layer (parser and argv binding);
   - command use-case layer (session lifecycle operations);
   - contract/presentation layer (stable result model, json/text rendering, exit-code mapping).
7. Stable command result contract (internal, shared by all commands):
   - fields: `command`, `session_id`, `status`, `event_code`, `message`, `errors`, `data`;
   - transport-independent: the same contract is rendered in text and json;
   - parser replacement must not change this contract.
8. ADR boundaries:
   - ADR 007 defines command surfaces and process contract;
   - ADR 008 defines default/override path policy (`work_dir`, `storage_dir`);
   - ADR 009 defines detailed component introspection schema for `help-components`;
   - ADR 010 stays optional for v1 and does not block ADR 007 implementation.

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

### D. Rich CLI framework now (`typer`/`click`)
Pros: faster command composition, richer help UX, easier shell completion later.  
Cons: adds runtime dependency before it is needed; raises migration and maintenance surface for phase 1.

### E. `argparse` with transport-independent architecture (chosen)
Pros: no new dependency now, explicit separation of parser from command semantics, cheap future migration to
another parser because use-cases and contract stay unchanged.  
Cost: more explicit boilerplate in parser wiring in exchange for long-term portability.

## Consequences

- A dedicated CLI entrypoint module is required.
- Packaging must expose a stable executable command (`console_scripts`).
- Command-level tests become part of release acceptance.
- Existing Python API remains unchanged and is treated as implementation backend for CLI commands.
- The process contract becomes an API surface and must be versioned and regression-tested as strictly as
  Python-level APIs.

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

Practical implementation design in the current project:

1. Module structure in `src/workflow_engine/`:
   - `cli.py` — `main(argv)` only, parser creation, command dispatch call;
   - `cli_contract.py` — result types (`CommandStatus`, `CommandResult`);
   - `cli_use_cases.py` — one function per command (`run`, `resume`, `set_limit`, `show_state`,
     `list_sessions`, `help_components`) that returns `CommandResult`;
   - `cli_presenters.py` — `render_text(result)` and `render_json(result)` only;
   - `cli_exit_codes.py` — pure mapping `CommandResult -> int`.
2. Parser responsibilities:
   - parse argv, validate syntactic argument shape, select command;
   - build configuration/bootstrap arguments;
   - call one use-case function;
   - print rendered output and return mapped exit code.
3. Use-case responsibilities:
   - call `Bootstrap(...).build_engine()` and existing `WorkflowEngine` methods;
   - convert `PresentResponse`, `StateModel`, and engine exceptions into `CommandResult`;
   - never print directly and never read argv directly.
4. Contract responsibilities:
   - define status vocabulary (`completed`, `paused`, `failed`, `setup_error`);
   - enforce that every command returns the same top-level fields;
   - keep extra command-specific payload only inside `data`.
5. Exit-code policy implementation:
   - `completed -> 0`;
   - `paused -> 2`;
   - `failed -> 3`;
   - `setup_error -> 4`;
   - mapping is centralized in `cli_exit_codes.py`, not duplicated in command functions.
6. `pyproject.toml` changes for v1:
   - add `[project.scripts] workflow-engine = "workflow_engine.cli:main"`;
   - no parser library dependency additions for ADR 007.
7. Test suite shape (`pytest`):
   - add `tests/cli/` command contract tests;
   - test via subprocess (`python -m workflow_engine.cli ...`) to verify real process behavior and exit codes;
   - cover both `text` and `--json` output modes for each command;
   - include negative scenarios: missing workflow path, unknown session, invalid limit argument,
     setup failure workflow.
8. End-to-end acceptance scenario for session lifecycle:
   - `run` with limit that triggers pause;
   - verify pause exit code and event code;
   - `set-limit` to raise limit;
   - `resume` to completion;
   - `show-state` confirms persisted terminal session event.
9. Best-practice constraints for implementation:
   - no business logic in parser layer;
   - single source of truth for status and exit code mapping;
   - no prose parsing of engine output to infer status;
   - preserve backward compatibility of `WorkflowEngine` Python API;
   - keep command payload deterministic and machine-readable.

Minimum command acceptance for phase 1:
- run from CLI with defaults;
- run with explicit `work_dir` and `storage_dir`;
- hit limit and resume after `set-limit`;
- list available components and details by name;
- deterministic exit codes and stable json schema across commands.

## Change log

- Initial draft opened from phase 1 architecture planning session.
- Added v1 parser strategy (`argparse`) with transport-independent CLI architecture and practical implementation
  blueprint for current repository layout.
