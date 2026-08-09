# ADR 006: Data flow between nodes

## Status
Accepted

## Active branch
—

## Context

The engine can run a linear workflow. It cannot yet be trusted with a multi step branching workflow,
because there is no contract for how data travels from one node to the next.

Facts from the current code:

1. `StateModel` mixes two different things under one object:
   - a **journal** written by the engine: `outputs`, `errors`, `error_code`, `visit_counters`,
     `attempt_counters`, `guard_results`, `nodes_visited`;
   - a **bus** that actions mutate directly: `params`.
2. `ActionNodeOutput.output_text` is used both as a human readable message and as a data carrier.
3. `ActionNodeOutput.parameters` is an undocumented second channel. `update_parameters` copies it from
   the previous output into the next one. It is not persisted, so resume may diverge from a straight run.
4. Collection actions mutate data in place (`append`, `popleft`) through references from `state.params`.
5. `StateModel.artifacts` exists and is persisted, but artifact creation does not register outputs there.
6. Actions needed for the acceptance scenario are partly unregistered and inconsistent with their own
   function signatures.

The acceptance scenario for this decision is concrete: scan a folder, push its entries into a queue, loop
over the queue, branch on file versus folder, collect per file information, and write a sorted table into
an artifact.

This is a single developer project. The decision is the smallest contract that makes such a workflow work,
survive a resume, and be debuggable.

## Decision

### 1. Ownership split: engine journal, engine-managed bus

- The journal belongs to the engine and stays write-only for engine logic.
- `state.params` remains the single persisted typed bus across non adjacent nodes.
- Actions may read from `state.params`, but they do not mutate it directly.

### 2. Node output channels are separated

- `output_text` is informational only (diagnostics, human readable messages).
- Workflow data flow uses a typed write set in `ActionNodeOutput`: `param_writes`.
- `update_parameters(prev_output)` and transient output-to-output parameter propagation are removed.

### 3. Parameter writes are applied by the engine and persisted immediately

- On each node execution, the engine applies `param_writes` into `state.params` through codecs.
- The state is persisted on every turn after applying writes.
- No "persist on stop only" mode is part of this ADR.

### 4. Namespace and overwrite policy

- `state.params` stays flat (keyed by parameter name).
- Default behavior is no implicit overwrite.
- `set` supports explicit upsert only with `allow_overwrite=true`.
- `replace` is strict and targets existing keys; `allow_overwrite` is ignored for `replace`.
- If a key exists and overwrite is not allowed, the node fails with a contract error
  (`param_overwrite_forbidden`).

### 5. Collections

- In-place collection mutation through shared references is not part of the contract.
- Queue/list updates are explicit write operations represented in `param_writes`.

### 6. Artifacts

- An artifact is a file under `work_dir/artifacts`.
- Artifact-producing actions must register artifacts in `state.artifacts`.
- `state.artifacts` stores structured metadata:
  - `logical_name -> WorkflowArtifact`
  - `WorkflowArtifact.relative_path` (path relative to `work_dir`)
  - `WorkflowArtifact.created_at` (timestamp)
  - `WorkflowArtifact.description` (`str | None`, static or resolved dynamically from action/function settings)
- Artifact creation is owned by functions: a function writes the file and returns artifact metadata in
  `ActionNodeOutput.artifacts`. There is no dedicated artifact action type; the artifact-producing node is
  an ordinary function node. The engine remains the enforcer of the artifact registration contract.
- Responsibility split is explicit:
  - function level (including external functions): may apply stricter pre-write checks and may fail early
    before overwrite/path-collision as a best-practice safety behavior;
  - engine level (mandatory contract): once artifact metadata is returned in `ActionNodeOutput.artifacts`,
    the engine registers factual latest state and records conflicts in `state.artifact_events`.
- Artifact registration follows a **state reflects reality** rule: when a function has already written files,
  the engine updates `state.artifacts` to the latest observed artifact metadata.
- Artifact overwrites are tracked as artifact-specific events, not as generic state warnings and not as
  default node-fatal errors.
- The engine checks two independent conflict cases during registration:
  - same `logical_name` already exists;
  - same `relative_path` is already bound to a different `logical_name`.

### 7. Guards

- Guards receive read-only input only: current node output and resolved references (`param.*`, `output.*`).
- Guards do not get mutable `state` and have no side effects.

### 8. Loop policy boundary

- ADR 006 includes only a minimal loop guardrail: engine-enforced `max_nodes_visited` with default off.
- Full retry/termination policy is deferred to a separate ADR.

### 9. Surface included in ADR 006 implementation

- `FunctionAction` and `FunctionsAction` are reshaped to the new contract, and artifact creation is served
  by functions through them instead of a dedicated artifact action.
- `PopFromQueue` is excluded from ADR 006 action surface and moved to specialized function-level behavior
  that returns declarative `param_writes`. The action is removed from the code base.
- `ForEachOutputParameterNode` is excluded from ADR 006 and may become a separate ADR topic. The action is
  removed from the code base; a future decision reintroduces it under the write set contract.

### 10. Session control event journal

- `StateModel` includes a dedicated session control journal: `state.session_events`.
- `state.session_events` is an append-only list of structured events and is persisted with state.
- Every external engine call is recorded in `state.session_events`, including successful and failed outcomes.
- The minimum normalized event shape is:
  - `event_id` (application-generated UUID)
  - `code`
  - `timestamp`
  - `actor` (`operator` | `engine`)
  - `details` (dictionary with event-specific fields such as old/new limit values)
- Minimum event coverage in ADR 006 scope:
  - `operator`: `session_created`, `workflow_started`, `operator_limit_updated`, `workflow_resumed`
  - `engine`: `workflow_setup_failed`, `workflow_paused_limit`, `workflow_completed`, `workflow_failed`
- `workflow_started` is emitted on the first run entry of a session and `workflow_resumed` on every later
  one. The distinction is derived from the persisted journal, so it holds across engine instances and
  process restarts; the in-memory engine cache is not a valid source for it.
- A call rejected before execution starts (workflow build/validation setup error) is still an external engine
  call and is recorded as `workflow_setup_failed`.
- The event list above is a minimum, not a closed set. A stop that waits for an operator (an interactive
  node) has no code in ADR 006, because no such node exists yet. When one is implemented, it brings its own
  event codes with it.
- Extended audit concerns (for example cross-service request correlation and idempotency policy) are
  deferred to a separate ADR.

## Alternatives considered

### A. Explicit split: engine journal, engine-managed bus (chosen)
Actions publish typed write sets, engine applies and persists them.

Pros: deterministic resume, single source of truth, auditable writes.  
Cost: rewrite collection and artifact actions, adjust tests and examples.

### B. Keep transient adjacent channel
Keep `ActionNodeOutput.parameters` as a short lived bridge between adjacent nodes.

Pros: fewer code changes now.  
Cons: resume divergence remains possible; data flow stays partly invisible and non debuggable.

### C. Formalize unrestricted state mutation
Allow actions to read and write state directly.

Pros: no immediate refactor effort.  
Cons: journal cannot be trusted; behavioral drift is hard to diagnose; rejected.

## Consequences

The implementation must:

1. Extend `ActionNodeOutput` with an explicit typed write set for parameter updates.
2. Remove transient output parameter propagation.
3. Apply parameter writes only in engine code and persist after each node turn.
4. Enforce overwrite policy with explicit opt-in.
5. Rework collection-oriented actions to explicit write semantics.
6. Register artifact outputs in `state.artifacts` as `WorkflowArtifact` entries (not plain string paths).
7. Add `WorkflowArtifact` serialization in state persistence (`to_dict`/`from_dict`).
8. Add artifact conflict event tracking in state persistence.
9. Deliver the folder scan acceptance scenario as an end to end test, including a resume run.
10. Add a persisted `session_events` journal in `StateModel`.
11. Record all external engine calls into `state.session_events` using the normalized event shape.
12. Record setup-time workflow validation/build failures as `workflow_setup_failed`.
13. Add test coverage for stop on limit, operator limit update, and resume to equivalent final results.

## Related ADRs

- ADR 002 node composition (Accepted): defines node shape and guard model.
- ADR 003 persistence boundary and run workspace (Accepted): defines `work_dir`.
- ADR 004 session bootstrap and configuration snapshot (Accepted): defines session resume boundary.

## Implementation notes

Acceptance scenario, delivered as an end to end test that builds its workflow from a temporary folder tree
rather than from a checked-in example file:

1. Scan a folder and push entries into a queue parameter.
2. Loop: pop one entry, branch on file versus folder, and push folder contents back to queue.
3. For files, collect attributes and append rows into an accumulator parameter.
4. When queue is empty, sort rows by file type and write a table artifact.
5. Resume mid loop and produce the same final artifact and parameters as a straight run.

Write contract details agreed after status move:

- `param_writes` is produced by action runtime code and returned in `ActionNodeOutput`; it is not
  declared as a workflow mapping DSL in `WorkflowNodeModel`.
- Engine is the only writer to `state.params`; it applies `param_writes` and persists state on every turn.
- `param_writes` entries are declarative operations, not callables.
- Minimal operation set in ADR 006 implementation:
  - `set`: create a new parameter; fail if key already exists.
  - `set` with `allow_overwrite=true`: explicit upsert.
  - `replace`: replace an existing value; fail if key does not exist.
    `allow_overwrite` is ignored for this mode.
  - `append`: append item(s) to `list` or `deque`; fail on type mismatch.
  - `dict_update`: shallow update for `dict`; fail on type mismatch.
- For collection parameters, explicit `replace` is allowed in addition to collection-specific modes.
- Engine-level apply failures use explicit contract errors (`param_overwrite_forbidden`,
  `param_type_mismatch`, `invalid_write_mode`).
- Artifact creation is served by functions that write the file and return metadata in
  `ActionNodeOutput.artifacts`; there is no dedicated artifact action type.
- `PopFromQueue` and `ForEachOutputParameterNode` are removed from the code base rather than left
  unregistered, because `PopFromQueue` mutated a queue in `state.params` in place, which this decision
  forbids.
- Queue-consumption behavior is implemented through functions that return `param_writes`, not through a
  dedicated `PopFromQueue` action.

Recommended artifact state shape for implementation:

```python
@dataclass(frozen=True)
class WorkflowArtifact:
    relative_path: str
    created_at: str
    description: str | None = None
```

Recommended artifact event shape for implementation:

```python
@dataclass(frozen=True)
class ArtifactEvent:
    code: str  # "artifact_overwritten" | "artifact_path_conflict"
    node_id: str
    logical_name: str
    relative_path: str
    timestamp: str
    message: str | None = None
```

- Keep events in an artifact-specific state field (`state.artifact_events`), not in a generic
  `state.warnings`.
- Default behavior: on conflict, update `state.artifacts` to factual latest metadata and append an event:
  - `artifact_overwritten` for same-name re-registration;
  - `artifact_path_conflict` for same-path registration under a different logical name.
- Do not fail the node by default.
- Function-level pre-check failures (before artifact registration) are allowed and can stop the node;
  this does not change the mandatory engine-side registration/event contract for artifacts that are returned.
- Strict failure-on-overwrite, if ever needed, is an optional policy switch and outside ADR 006 default.

Session event contract details agreed after status move:

- `session_events` is a dedicated state journal and is not part of `state.params`.
- Events are appended by engine/session entrypoints that handle external calls.
- Read-only informational calls may use dedicated codes and must still be auditable.
- Limit change events include old/new values in `details`.
- `details` values are restricted to JSON-serializable scalars, because the journal is persisted with the
  state.
- Each event carries `event_id` generated by the application as a UUID.
- On Python 3.13, this is implemented with stdlib UUID generation (for example `uuid4`).
- On migration to Python 3.14, prefer stdlib UUIDv7 for new event identifiers.
- Resume-equivalence acceptance scenario covers:
  - straight run without restrictive limit;
  - paused run with restrictive `max_nodes_visited`;
  - operator limit increase;
  - resume to completion with final equality of ADR contract surfaces.

Recommended payload shape for implementation:

```python
@dataclass(frozen=True)
class ParamWrite:
    mode: Literal["set", "replace", "append", "dict_update"]
    value: object
    allow_overwrite: bool = False
```

How this looks in `WorkflowNodeModel` configuration:

- `action_parameters` define only action inputs and static behavior settings.
- `param_writes` is not configured as a node-level mapping block.
- Action code computes writes at runtime and returns them in `ActionNodeOutput.param_writes`.

Example node configuration:

```json
{
  "id": "collect_file_info",
  "action_type": "function",
  "action_parameters": {
    "function_name": "collect_file_info",
    "function_parameters": {
      "file_path": "param.path_from_queue"
    }
  },
  "save_as": "last_result"
}
```

In this example, `save_as` may still persist `output_text` for diagnostics/history, while typed workflow
state updates (for example appending a row into `table_rows`) are returned by the action itself through
`ActionNodeOutput.param_writes` and applied by the engine.

## Change log

- Initial draft created to open the data flow discussion with the folder scan scenario.
- Status moved from Draft to Implementing.
- Decision settled: engine-only parameter writes via typed write sets, immediate persistence, flat namespace
  with explicit overwrite opt-in, explicit artifact registration, and `ForEachOutputParameterNode` excluded
  from scope.
- Artifacts contract clarified: keep dedicated `CreateArtifactActionWithContent` surface (function-backed),
  persist structured metadata in `StateModel.artifacts` via `WorkflowArtifact`, and exclude `PopFromQueue`
  from ADR 006 action surface in favor of function-level queue operations.
- Artifact conflict policy clarified: state tracks factual latest artifact metadata and records
  registration conflicts in `state.artifact_events` (`artifact_overwritten`, `artifact_path_conflict`)
  as audit signals, non-fatal by default.
- Session control event contract added: `state.session_events` now records all external engine calls
  with normalized structured events.
- Session control event contract simplified: use application-generated UUID `event_id`;
  Python 3.14 migration should switch new IDs to stdlib UUIDv7.
  extended audit policy is deferred to a separate ADR.
- Session control event contract clarified during implementation: `workflow_started` and
  `workflow_resumed` are decided from the persisted journal, the event list is a minimum rather than a
  closed set, and a stop that waits for an operator is left without a code until an interactive node
  exists.
- Setup-error call semantics finalized: workflow setup/build failures are recorded as
  `workflow_setup_failed` so every external engine call stays auditable.
- Artifact surface aligned with the delivered implementation: artifact creation is function-backed through
  ordinary function nodes, and the dedicated `CreateArtifactActionWithContent` action surface is dropped.
- Excluded actions resolved: `PopFromQueue` and `ForEachOutputParameterNode` are removed from the code base
  instead of being kept unregistered.
- Acceptance scenario restated as an end to end test rather than a checked-in example workflow; the stale
  `examples/colect_file_info_workflow.json` is deleted.
