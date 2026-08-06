# ADR 006: Data flow between nodes

## Status
Implementing

## Active branch
feature/adr_006-data-flow-between-nodes

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
- Artifact-producing actions must register artifacts in `state.artifacts`
  (logical name -> relative path).

### 7. Guards

- Guards receive read-only input only: current node output and resolved references (`param.*`, `output.*`).
- Guards do not get mutable `state` and have no side effects.

### 8. Loop policy boundary

- ADR 006 includes only a minimal loop guardrail: engine-enforced `max_nodes_visited` with default off.
- Full retry/termination policy is deferred to a separate ADR.

### 9. Surface included in ADR 006 implementation

- `FunctionsAction`, `PopFromQueue`, and `CreateArtifactActionWithContent` are reshaped to the new contract.
- `ForEachOutputParameterNode` is excluded from ADR 006 and may become a separate ADR topic.

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
6. Register artifact outputs in `state.artifacts`.
7. Update the folder scan example and add an end to end resume scenario.

## Related ADRs

- ADR 002 node composition (Accepted): defines node shape and guard model.
- ADR 003 persistence boundary and run workspace (Accepted): defines `work_dir`.
- ADR 004 session bootstrap and configuration snapshot (Accepted): defines session resume boundary.

## Implementation notes

Acceptance scenario, delivered as an example workflow and an end to end test:

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
