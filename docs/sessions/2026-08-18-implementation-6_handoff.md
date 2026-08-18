# Session note

## Type
implementation

## Goal
Implement ADR 011 (artifact addressing and export contract) end to end: `artifact.` references,
`deliverables` declaration with engine export on completion, and the `export-artifact` salvage
command with additive CLI result keys.

## Completion criteria
- `artifact.<name>` resolves through the engine reference resolver; an unknown name is the node
  contract error `artifact_not_found`.
- `copy_artifact` copies and registers an artifact (copy-promote), copy-only.
- Workflow definitions accept a validated optional `deliverables` block.
- On terminal completion the engine exports declared deliverables to `--export-dir` or config
  `export_dir`, with non-fatal, auditable outcomes.
- `export-artifact` extracts one artifact or all deliverables for any run outcome.
- run/resume/show-state additively surface absolute artifact paths and the deliverables list.
- pytest and ruff green from the command line.

## Scope boundaries
- No change to the existing `param.`/`output.` raise-on-missing behaviour.
- No move/delete artifact semantics (needs a deregistration contract; out of scope per ADR 011).
- No remote/non-filesystem export targets.
- ADR body was not rewritten to the as-built wording and the ADR was not frozen; that is the
  follow-up architecture session at merge time.

## Status
completed

## Result
Delivered on the feature branch in three reviewable commits, each green on pytest and ruff:
1. Reference resolver consolidated into one prefix dispatch in `StateModel.set_parameters` with the
   third kind `artifact.<name>`; `ArtifactNotFoundError` caught in `BaseAutomaticAction.execute` and
   turned into the `artifact_not_found` node error value; `copy_artifact` added.
2. `WorkflowModel.deliverables` (shape-validated, round-trips through storage); three engine session
   events (`deliverable_missing`, `artifact_export_failed`, `artifacts_exported`) all mapped to
   COMPLETED in status derivation; `artifacts_export.export_deliverables_on_completion`; engine
   export step on completion with CLI-over-config precedence; config `export_dir`.
3. `export-artifact` command (required mutually exclusive `--artifact-name`/`--all`); `--export-dir`
   on run/resume; additive result keys (`artifacts` absolute+description and `deliverables` on
   run/resume, `artifacts_absolute`+`deliverables` on show-state); `artifact.` added to the
   reference-prefix help docs.
Full suite: 175 tests pass; ruff clean.

## Decisions
- `artifact_not_found` is a node contract error value, not an escaping exception, realised through
  the existing `ArtifactPathError` catch pattern. Follows ADR 011 implementation notes over the
  looser "symmetric to param./output." wording in the decision section.
- `export-artifact` records no session events. The three export event codes map to COMPLETED, so
  recording one on a paused or failed session would corrupt the status derived from the last event;
  the salvage command therefore only copies and returns data.
- To keep contract stability, show-state keeps `artifacts` (relative) and adds `artifacts_absolute`;
  run/resume have no prior `artifacts` key, so it carries the absolute+description map there.

## Open questions
None blocking. The ADR text still describes the decision "as imagined"; align it to as-built at
freeze.

## Next steps
1. Open the ADR 011 review/freeze architecture session: verify against requirements, merge the
   feature branch into `development`, align Context/Decision/Consequences to the delivered result,
   set status Accepted, clear the active branch in the ADR body and registry.
2. Consider an `examples/` workflow that declares a deliverable, as an operator-facing template.

## References
- Branch: `feature/adr_011-artifact-addressing-and-export`
- ADR: `docs/adr/adr-011-artifact-addressing-and-export.md`
- Touched: `models/state.py`, `models/workflow.py`, `exceptions.py`, `actions/base_actions.py`,
  `actions/create_artifact_functions.py`, `actions/base_functions.py`, `actions/action_nodes.py`,
  `artifacts_export.py` (new), `engine.py`, `bootstrap/bootstrap.py`, `bootstrap/config_loader.py`,
  `cli/contract.py`, `cli/use_cases.py`, `cli/main.py`; tests `test_state.py`,
  `test_create_artifact_functions.py`, `test_artifacts_export.py` (new),
  `test_cli_export_artifact.py` (new).
