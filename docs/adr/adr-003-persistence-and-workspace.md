# ADR 003: Persistence boundary and run workspace

## Status
Draft

## Active branch
None

## Context

A workflow run needs both persistent data and a real local workspace.

- Persistent data: `WorkflowModel` and `StateModel`, saved each turn so a run can resume.
- Workspace data: generated files and artifacts, consumed by tools that require filesystem paths.

This application is intentionally workspace-dependent: every run must have a local directory.
Current and planned behavior:

- Start without `--session`: create a new session UUID.
- Ensure `.workflow-engine` exists in the launch directory.
- Create `.workflow-engine/<session_id>` and use it as `work_dir` for the run.

The issue is not whether `work_dir` is required. It is required. The issue is where this
requirement is enforced in architecture boundaries.

Today `Storage` also creates the initial state via `start_workflow`, so `Storage.__init__(working_dir)`
is currently consistent with implementation. But this couples run bootstrapping to persistence.
For a database backend this forces constructor parameters that belong to run context, not to medium.

## Decision

`work_dir` remains a mandatory run invariant, but run bootstrapping moves out of persistence.

- `Engine` owns run start and creates initial `StateModel`, including `state.work_dir`.
- `Storage` owns persistence only: load and save workflow/state data.
- `Storage` abstract contract does not require `working_dir` in its base constructor.
- Concrete backends define their own constructor needs:
  - file backend (`JsonStorage`): may require a directory;
  - database backend (`MySqlStorage`): may require DB connection/config.

Because there is no separate Session abstraction yet, this orchestration is implemented in `engine.py`
as the transitional owner of `start_workflow`.

`work_dir` stays in `StateModel` and is persisted as run metadata so resumed runs can find their files.

## Alternatives considered

### A. Keep `start_workflow` in `Storage` and keep mandatory `working_dir` in base constructor
Pros: minimal refactor now.
Cons: `Storage` remains a mixed abstraction (persistence + run orchestration), and every backend must
carry run-context constructor state.

### B. Move run start to `Engine` and keep `Storage` as persistence only
Pros: clean separation of concerns; database backends persist state including `work_dir` without
constructor coupling to filesystem context.
Cons: caller must provide run context (`work_dir`) to engine start flow.

### C. Store workspace artifacts in persistence backend (including DB)
Pros: one storage location for all outputs.
Cons: external tools still need real filesystem paths; materialization to disk is still required and
adds complexity/cost.

Chosen: **B**.

## Consequences

- The system still requires a local `work_dir` for every run.
- `work_dir` is mandatory in `StateModel` regardless of backend type.
- `MySqlStorage` persists `state.work_dir` as data and does not need it as constructor requirement.
- `JsonStorage` may still use the session workspace directory for files (`state.json`, `workflow.json`).
- Existing callers of `Storage.start_workflow` must switch to engine-level run start API.
- Startup behavior is explicit and testable in one place (`engine.py`) until a dedicated Session layer exists.

## Related ADRs

- ADR 002 node composition.
- ADR 001 exception architecture.

## Implementation notes

Planned implementation sequence:

1. Add engine-level run start API in `engine.py`:
   - input: `storage`, workflow definition path or data, `work_dir`;
   - output: initial `StateModel`, `WorkflowModel`.
2. Move initial state creation (`timestamp`, `work_dir`, `schema_version`, `flow_id`, `current_node_id`)
   from `Storage.start_workflow` to engine-level API.
3. Keep `work_dir` persisted in state for resume.
4. Adapt `JsonStorage` to persistence-only behavior and preserve current file layout if possible.
5. Add/adjust tests for:
   - new session path creation and assignment as `state.work_dir`;
   - resume behavior with persisted `work_dir`;
   - backend parity (file backend and DB backend contract expectations).

Open points:

- Workflow definition source at engine boundary: path only, data only, or both.
- Strictness of `work_dir` validation during load in DB resume scenarios.
- Whether to keep `Storage.start_workflow` temporarily as compatibility wrapper and deprecate it.

## Change log

- Reframed the decision after architecture review: mandatory `work_dir` is a run-level invariant, not
  a persistence constructor invariant.
- Chosen boundary clarified: move run start orchestration to `engine.py` until Session abstraction exists.
