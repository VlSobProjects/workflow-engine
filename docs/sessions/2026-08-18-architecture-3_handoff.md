# Session note

## Type
architecture

## Goal
Decide the artifact access and export contract (finding 2 of the 2026-08-18 investigation) and open
it as a Draft ADR 011 with the decision, the alternatives and the trade-offs recorded.

## Completion criteria
1. The decision space is decomposed and each sub-decision is discussed in critical mode with at
   least two alternatives and their costs.
2. ADR 011 exists as a Draft on `development` with Context, Decision, Alternatives and Consequences
   filled, and its registry row is added.
3. The scope boundary against the standalone bug-fix session (empty-root failure, CLI param-mode
   crash) is stated explicitly in the ADR.

## Scope boundaries
- No production code is changed; this session produces the Draft ADR and its registry row only.
- The empty-root `dict_list_to_pretty_table` failure and the `resume` param-injection crash stay in
  their own bug-fix session.
- Workflow templating (placeholder substitution) is out of scope.

## Status
completed

## Result
The artifact access and export gap was decomposed into three sub-decisions (in-workflow addressing,
sandbox export, CLI surfacing), each discussed with alternatives and costs, and the outcome was
opened as Draft ADR 011 on `development` with its registry row. The stale ADR 010 registry row
(Implementing with an active branch, while the frozen ADR body says Accepted) was corrected in the
same change.

## Decisions
1. Addressing (ADR 011 §1): a third engine-resolved reference kind `artifact.<logical_name>`
   resolving to the absolute path at node execution time; `artifact_not_found` on a missing name.
   A dedicated state-reading function was rejected because it caches a second copy of the path in
   `state.params`.
2. Export (ADR 011 §2–3): an optional top-level `deliverables` block in the workflow definition
   declares *what* the workflow produces; the operator supplies *where* (`--export-dir`, then
   config `export_dir`, otherwise no auto-export); the engine exports deliverables only on
   completion with non-fatal `deliverable_missing` / `artifact_export_failed` events. A dedicated
   export action type was rejected (contradicts the ADR 006 no-artifact-action precedent and mixes
   delivery into control flow); relaxing the artifacts root was rejected (breaks the ADR 006
   invariant).
3. CLI (ADR 011 §4): a new `export-artifact` salvage command for any run outcome, and additive
   result keys — artifacts with absolute POSIX paths in terminal `run`/`resume` data and in
   `show-state`.
4. Scope: the empty-root failure and the `WriteParamMode` resume crash stay in a standalone
   bug-fix session; workflow templating stays a separate future decision.

5. `export-artifact` requires exactly one of an artifact name or an explicit `--all`; a bulk
   export never happens by default (settled in a session follow-up, recorded in the ADR 011
   change log).

## Open questions
None.

## Next steps
1. Open the standalone bug-fix session for the empty-root failure (finding 3) and the CLI
   param-mode crash (finding 6) of the investigation note.
2. When ADR 011 moves beyond Draft, decide Draft-to-Implementing directly or via POC of the
   reference-resolver consolidation.
3. The implementation session for the examples/README remainder (decision 4 of the investigation
   note) stays queued.

## References
- Source: [2026-08-18-investigation-1_handoff.md](2026-08-18-investigation-1_handoff.md)
- Related: ADR 006 (artifact registration contract), ADR 007 (CLI contract), ADR 008 (path policy).
- Branch: development (Draft ADRs are written directly on `development`).