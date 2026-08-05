# ADR 003: Persistence boundary and run workspace

## Status
Accepted

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
- Current implementation keeps a temporary coupling (`WorkflowSessions` creates `JsonStorage`) and assumes
  resume under the same session root; this limitation is tracked as follow-up architecture work.

## Related ADRs

- ADR 002 node composition.
- ADR 001 exception architecture.
- ADR 004 session bootstrap and configuration snapshot (Implementing, follow-up).

## Implementation notes

Implemented in this branch:

1. Run start moved out of `Storage` into `WorkflowSessions` in `engine.py`.
2. `Storage` base contract now keeps `session_id` and persistence methods only.
3. `JsonStorage` now resolves state/workflow files under `<root>/<session_id>/`.
4. Session creation now persists `StateModel` with explicit `work_dir` and `session_id`.
5. Engine entry was made internal (`_start_engine`) and is called through `WorkflowSessions`.

Open follow-up moved to ADR 004:

- Backend selection and session-level storage snapshot.
- Backend-independent session resume (`session_id` lookup to stable session metadata).
- Session registry contract (`session_id -> storage profile + work_dir`).

## Change log

- Reframed the decision after architecture review: mandatory `work_dir` is a run-level invariant, not
  a persistence constructor invariant.
- Chosen boundary clarified: move run start orchestration to `engine.py` until Session abstraction exists.
- Status changed to `Implementing`; implementation completed in branch
  `feature/adr-003-persistence-and-workspace`, with deferred bootstrap/config concerns moved to ADR 004.
- Freeze gate passed after merge into `development`; status changed to `Accepted`.
