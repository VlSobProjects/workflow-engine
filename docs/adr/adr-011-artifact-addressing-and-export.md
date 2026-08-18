# ADR 011: Artifact addressing and export contract

## Status
Draft

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
- Referencing an unregistered artifact is a contract error and fails the node under
  `artifact_not_found`, symmetric to unresolved `param.`/`output.` references.
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

- New command `export-artifact`: copies one named artifact (or all deliverables when no name is
  given) of an existing session to a target directory. It works for completed, paused and failed
  sessions and is the manual/salvage path.
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

- Resolution target of `artifact.<name>` is the absolute path in POSIX form; state continues to
  persist relative paths only.
- `export-artifact` result data should include the concrete target paths written.
- The e2e acceptance scenario is the operator flow from the 2026-08-18 investigation: scan a tree,
  declare the CSV as a deliverable, run with `--export-dir`, and find the CSV in the operator
  folder with its path in the result output; plus a salvage run where a paused session's artifact
  is extracted by command.

## Change log

- Draft opened from the 2026-08-18 architecture session, capturing finding 2 of the 2026-08-18
  operator investigation as context.