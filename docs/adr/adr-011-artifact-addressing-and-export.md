# ADR 011: Artifact addressing and export contract

## Status
Accepted

## Active branch
—

## Context

ADR 006 made artifacts first-class state: a function writes a file under `work_dir/artifacts`,
returns metadata in `ActionNodeOutput.artifacts`, and the engine registers it in `state.artifacts`.
The 2026-08-18 operator investigation confirmed that a registered artifact is effectively locked
inside the session sandbox:

1. A node cannot reference an artifact's real path. No registered function exposes
   `state.artifacts`, and the natural attempt (`copy_file` with `path_source: output.<NODE>`) fails
   because `output_text` is an informational message (`pretty_table_created`), not a path — by
   ADR 006 design.
2. The artifact cannot leave the sandbox from within a workflow: artifact path resolution rejects
   any path outside `work_dir/artifacts`, and that invariant (relative paths in state, resume
   semantics, conflict detection) must hold.
3. The operator never receives the artifact location: `run`/`resume` results carry only `work_dir`;
   `show-state` exposes `artifacts_path` and a relative-path `artifacts` map that the operator must
   join by hand.

So a workflow whose whole purpose is to produce a file (the folder-inventory-to-CSV scenario) ends
with the operator digging the file out of a hidden session directory manually. If artifacts are the
primary product of a workflow, they must be part of its interface, not an implementation detail of
its sandbox.

Constraints:
- The ADR 006 artifact-root invariant stays: artifacts live under `work_dir/artifacts`, state keeps
  relative paths, export is an explicit copy.
- The CLI result contract (ADR 007/009) is stability-bound: existing keys and nesting do not
  change; extension is additive only.
- Destination directories are session/operator concerns and must not be hardcoded in workflow
  definitions (the `examples/` cleanup removed exactly such personal absolute paths).

## Decision

Artifacts become addressable and extractable through one model: a workflow declares which artifacts
are its deliverables, nodes address artifacts through engine-resolved references, the engine exports
deliverables on completion to an operator-supplied destination, and the CLI always surfaces and
extracts artifacts regardless of how the run ended.

### 1. Artifact references: `artifact.<logical_name>`

- A third reference kind joins `param.` and `output.`: `artifact.<logical_name>` resolves to the
  absolute path (POSIX form) of the registered artifact at the moment the node executes.
- Resolution is engine-owned, in the same resolver that serves `param.` and `output.`; guards see
  resolved values the same way they do today.
- `state.artifacts` remains the single source of truth: the reference is resolved per execution and
  never cached into `state.params`.
- Referencing an unregistered artifact is a node contract error: `artifact_not_found` is returned
  as the node error value (not raised as an engine-level exception), consistent with ADR 001/006.
  Unlike `param.`/`output.` missing references, which raise `StateLoadParameterError` and escalate
  as engine errors, `artifact_not_found` is caught at the action level so a missing artifact fails
  only the node, not the engine.
- With this, in-workflow export needs no new component: `copy_file` with
  `path_source: artifact.<name>` and an operator-provided target is the supported in-graph pattern.

### 2. Deliverables declaration in the workflow definition

- The workflow definition gains an optional top-level `deliverables` block: an ordered list of
  logical artifact names that constitute the product of the workflow.
- The declaration states *what* the workflow produces; it never states *where* it goes.
- Deliverables are validated at build time only for shape (a list of non-empty unique names); the
  named artifacts may legitimately not exist until runtime.
- The declaration is introspectable: it is part of the definition and surfaces through the CLI
  result data.

### 3. Engine export on completion

- When a run reaches `workflow_completed` and an export destination is known, the engine copies
  each declared deliverable from `work_dir/artifacts` into the destination directory.
- Destination precedence: `--export-dir` CLI option, then `export_dir` in the configuration file.
  If neither is set, no automatic export happens; deliverables remain visible in result data and
  extractable by command.
- Export happens only on completion. Paused and failed runs never auto-export; their artifacts are
  retrieved with `export-artifact`.
- Export outcomes are non-fatal and auditable:
  - a declared deliverable missing from `state.artifacts` at completion records a
    `deliverable_missing` session event;
  - a failed copy records an `artifact_export_failed` session event;
  - in both cases the workflow status remains `completed`; delivery problems do not annul the
    completed work.
  - successful export is recorded as an `artifacts_exported` session event with the exported names
    and destination in `details`.

### 4. CLI extraction and surfacing

- New command `export-artifact`: copies one named artifact of an existing session to a target
  directory, or all declared deliverables when `--all` is given. The artifact name and `--all` are
  mutually exclusive and exactly one is required, so a bulk export is always an explicit choice.
  The command works for completed, paused and failed sessions and is the manual/salvage path.
- Terminal `run`/`resume` results additively gain an `artifacts` entry in `data`: a map of logical
  name to absolute POSIX path plus description, and the `deliverables` list.
- `show-state` additively exposes the absolute path per artifact; the existing `artifacts_path` and
  relative-path map stay unchanged.

## Alternatives considered

### A. Dedicated export action type
An `export_artifact` action used as a graph node.

Pros: no schema change; export is visible in the graph.
Cons: contradicts the ADR 006 precedent that artifact work has no dedicated action type; mixes
delivery into control flow with muddy failure semantics (a failed copy fails a workflow whose real
work succeeded); redundant once `artifact.` references exist, because `copy_file` already covers
in-graph copying. Rejected.

### B. CLI export command only
`export-artifact` without deliverables declaration or engine export.

Pros: smallest change surface; no workflow-schema growth.
Cons: the workflow interface never states what it produces; every retrieval is a manual second
step; automation of the produce-and-deliver scenario stays impossible. Rejected as the sole
mechanism; the command itself is kept as the salvage path.

### C. Relax the artifact root
Allow artifact paths outside `work_dir/artifacts` so functions write directly to the destination.

Pros: no export step at all.
Cons: breaks the ADR 006 invariant — relative paths in state, resume semantics and conflict
detection all assume one root; sandbox isolation is lost silently. Rejected.

### D. Deliverables declaration with engine export and salvage command (chosen)
Declaration states what, operator states where, engine exports on completion, CLI command covers
every other case.

Pros: artifacts become part of the workflow interface (industry precedent: CI `artifacts:` blocks,
Nextflow `publishDir`); mechanism/policy separation keeps the graph clean; every outcome path has a
retrieval story.
Cost: the widest surface of the alternatives — schema, engine hook, CLI option, command, contract
keys.

## Consequences

Enables:
- The folder-scan scenario ends with the CSV in the operator's folder, by declaration or by one
  command, with the path always printed in the result.
- Workflows can chain artifact-consuming steps (`artifact.` references) without ad hoc path
  plumbing.
- Tooling can read what a workflow produces without running it.

Costs:
- Workflow schema grows a top-level block (loader validation, help contract, docs).
- The engine gains a post-completion export step and three session event codes.
- CLI grows one command and one option; the result contract grows additive keys.
- The reference resolver gains a third prefix; its current string-matching implementation should be
  consolidated rather than extended ad hoc.

Closes off:
- Writing artifacts directly outside `work_dir/artifacts` stays forbidden; export is always an
  explicit copy.
- Destination paths in workflow definitions stay forbidden.

Trust boundary:
- The engine guards its own write path (artifact path resolution and registration); it does not
  police the filesystem side effects of functions. A function wired by the workflow author can
  delete or modify files under `work_dir/artifacts` — that is a deliberate authoring choice, and
  the engine does not try to prevent it or reconcile `state.artifacts` afterwards.
- A stale registration is tolerated because every consumer of it has a defined failure mode, never
  undefined behavior: an `artifact.` reference still resolves but the consuming node fails with
  its own file-level error, the completion export records a non-fatal `artifact_export_failed`,
  and `export-artifact` exits with a resolution error for the missing file.

Out of scope:
- The empty-root `dict_list_to_pretty_table` failure and the `resume` param-injection
  `WriteParamMode` crash are standalone defects handled in a bug-fix session; neither depends on
  this decision.
- Workflow templating (placeholder substitution for parameters like the scan root) is a separate
  future decision.
- Remote or non-filesystem export targets are out of scope; the destination is a local directory.

## Related ADRs

- ADR 006 data flow between nodes (Accepted): artifact registration contract and root invariant
  this decision builds on.
- ADR 007 CLI contract (Accepted): result-shape stability rules the additive keys must follow.
- ADR 008 path policy (Accepted): destination precedence mirrors its CLI-over-config rule; POSIX
  path form.
- ADR 009 operator help contract (Accepted): deliverables and the new command surface through it.

## Implementation notes

### Reference resolution (`artifact.<name>`)

- The resolution point is `StateModel.set_parameters` (`src/workflow_engine/models/state.py`),
  which today string-matches the `param.` and `output.` prefixes. Adding the third prefix should
  consolidate the matching into one prefix-dispatch table instead of extending the `if/elif`
  chain; `StateReadOnlyView.set_parameters` delegates there, so guards and action parameter
  resolution pick the prefix up through the existing path with no separate guard-side work.
- The absolute path is built by joining the artifacts root (`work_dir/artifacts`) with the stored
  `WorkflowArtifact.relative_path` and rendering it in POSIX form. State persistence is unchanged:
  only relative paths are stored.
- A reference to a name absent from `state.artifacts` must surface as the node contract error
  `artifact_not_found` — an error value on the node result, consistent with ADR 001/006 — not as a
  raised `StateLoadParameterError` escaping to the caller.
- Resolution reads `state.artifacts` at each node execution; the resolved path is never written
  into `state.params`.

### Workflow schema (`deliverables`)

- The definition model gains an optional top-level `deliverables: list[str]`. Build-time
  validation (aggregated with the other configuration errors per ADR 001): a list, entries are
  non-empty strings, no duplicates. No check against registered artifact names — they exist only
  at runtime.
- An absent block and an empty list are equivalent: nothing is auto-exported and `export-artifact
  --all` has nothing to select.

### Engine export step

- Export runs inside the completion path, when the run reaches its terminal `workflow_completed`
  state and a destination is resolved. Copies preserve the artifact's relative path under the
  destination directory (so `tables/report.csv` stays `tables/report.csv`), creating parent
  directories as needed. An existing file at the target is overwritten: the destination is
  operator-owned and re-export must be idempotent.
- New members of `SessionEventCode` (engine actor): `DELIVERABLE_MISSING`,
  `ARTIFACT_EXPORT_FAILED`, `ARTIFACTS_EXPORTED`. `details` carries the logical names and, for
  exports, the destination and concrete target paths; for failures, the OS error message.
- Trap: `StateModel.get_workflow_status_code` derives the workflow status from the **last**
  session event. Export events are appended after `workflow_completed`, so all three new codes
  must map to `COMPLETED` in that match — otherwise a completed-and-exported session reports an
  unknown status.
- Export failures never change the workflow status and never raise; they end in the event journal
  and in the command result data.

### Artifact function surface: `copy_artifact`

- One registered function ships with this decision, because the deliverables story is incomplete
  without it: the copy-promote pattern (draft artifacts on working nodes, one final artifact
  promoted to a declared deliverable when ready) has no vehicle today — `copy_file` copies the
  file but registers nothing, so the copy cannot be declared or exported.
- Signature: `copy_artifact(source_artifact_name, target_artifact_name, target_path=None,
  allow_overwrite=False)`.
  - `source_artifact_name`: logical name of an existing artifact; unknown name is the function
    error `artifact_not_found`.
  - `target_artifact_name`: logical name of the new artifact.
  - `target_path`: path of the copy, resolved inside `work_dir/artifacts` through the existing
    artifact path resolution (outside paths stay rejected). When omitted, the copy lands in the
    artifacts root under the target artifact name with the source file suffix, following the
    default-path precedent of `dict_list_to_pretty_table`.
  - `allow_overwrite`: default `False`. When `False`, an existing target logical name or an
    existing registration of the target path fails early with the function-level error codes
    `artifact_overwritten` / `artifact_path_conflict` (the ADR 006 responsibility split: strict
    function pre-checks; engine registration of returned artifacts stays unchanged). When `True`,
    the copy proceeds and the engine records the ADR 006 conflict events as usual.
- The function copies only; it never moves. Move/delete would require a deregistration semantic
  that the ADR 006 registration contract does not have — that is a separate future decision, out
  of scope here. The source artifact stays registered and on disk inside the session sandbox.
- Documentation is part of the deliverable: full registration metadata (summary, `Annotated`
  parameter docs, error codes in the docstring), enforced by the ADR 009 quality gate so the
  function is complete in `help-component`.

### CLI surface

- `run`/`resume` gain `--export-dir`; the config file gains `export_dir`. Precedence follows the
  ADR 008 pattern: CLI option, then config value, then no auto-export. The resolved destination is
  recorded in the `artifacts_exported` event details.
- `export-artifact` arguments: the session id, a target directory, and exactly one of
  `--artifact-name` or `--all` (argparse mutually exclusive group, required). `--all` selects the
  declared deliverables; it is an error (exit 4) when the definition declares none. Copy semantics
  are identical to the engine export step. Exit codes per ADR 007: `0` on success, `4` for
  resolution errors (unknown session, unknown artifact name, missing artifact file, unwritable
  target).
- Additive result keys: terminal `run`/`resume` and `show-state` data gain per-artifact absolute
  POSIX paths and the `deliverables` list; `export-artifact` data lists the exported logical names
  with their concrete target paths. Existing keys (`artifacts_path`, the relative-path `artifacts`
  map) are untouched.
- Help surfaces (ADR 009): the reference-prefix documentation gains `artifact.`, and
  `export-artifact` joins the command surface; payload extension is additive only.

### Test surface

- Unit: prefix resolution (hit, `artifact_not_found`, no caching into params); `deliverables`
  schema validation errors; status derivation with each new event code as the last event;
  `copy_artifact` (default target path, overwrite refusal with both error codes, `allow_overwrite`
  path, unknown source).
- CLI contract: `export-artifact` argument matrix (name XOR `--all`, exit codes), destination
  precedence CLI-over-config.
- E2e, the operator flow of the 2026-08-18 investigation: scan a tree, declare the CSV as a
  deliverable, run with `--export-dir`, assert the CSV lands in the operator folder and its path
  appears in the result data; a salvage run where a paused session's artifact is extracted with
  `export-artifact`; an export-failure run (unwritable destination) asserting `completed` status
  plus `artifact_export_failed` in the journal.

## Change log

- Draft opened from the 2026-08-18 architecture session, capturing finding 2 of the 2026-08-18
  operator investigation as context.
- Bulk export made explicit: `export-artifact` requires exactly one of an artifact name or `--all`
  instead of defaulting to all deliverables, so an accidental bulk export is impossible.
  Implementation notes expanded with the concrete resolution point, schema validation, export
  copy semantics, event/status-derivation trap, CLI argument contract and test surface.
- `copy_artifact` added to the delivered surface: the copy-promote pattern (draft artifacts
  promoted to a declared deliverable) needs a function that copies and registers, which no
  existing component does. Copy-only by design — move/delete would need a deregistration
  semantic absent from ADR 006 and stay a separate future decision.
- Trust boundary recorded: the engine does not police filesystem side effects of functions inside
  `work_dir/artifacts`; stale registrations are tolerated because every consumer of one fails
  through an already-defined error path.
- Frozen as Accepted (2026-08-18): Decision §1 corrected to remove the misleading "symmetric to
  `param.`/`output.` references" phrasing — `artifact_not_found` is caught at the action level as
  a node error value, whereas `param.`/`output.` missing references raise `StateLoadParameterError`
  as engine-level errors; the Implementation Notes already stated this correctly.