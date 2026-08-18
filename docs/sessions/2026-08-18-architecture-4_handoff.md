# Session note

## Type
architecture

## Goal
Accept and freeze ADR 011 (artifact addressing and export contract): verify the implementation on
`feature/adr_011-artifact-addressing-and-export` against the ADR requirements, merge the feature
branch into `development`, align the ADR body with the delivered result, set status Accepted, and
synchronize the documentation.

## Completion criteria
- Implementation conformance confirmed against all ADR 011 acceptance criteria.
- Feature branch merged into `development` with no regression (pytest and ruff green).
- ADR 011 status set to Accepted; active branch cleared; Decision §1 aligned with the delivered
  behavior.
- `docs/adr/README.md` row updated to Accepted.
- `docs/sessions/README.md` registry updated with the implementation session 6 row and this session
  row.
- `docs/architecture/overview.md` updated with the artifact addressing and export section.

## Status
completed

## Result
All conformance criteria satisfied:
- `artifact.<name>` resolved via the consolidated prefix-dispatch in `StateModel._resolve_reference`.
- `ArtifactNotFoundError` caught in `BaseAutomaticAction.execute` and converted to node error value
  `artifact_not_found`.
- `WorkflowModel.deliverables` optional tuple, shape-validated at build time.
- Three new `SessionEventCode` values (`DELIVERABLE_MISSING`, `ARTIFACT_EXPORT_FAILED`,
  `ARTIFACTS_EXPORTED`) all mapped to `COMPLETED` in status derivation.
- `artifacts_export.py` export step called on completion; CLI-over-config export destination
  precedence implemented.
- `export-artifact` command with mutually exclusive `--artifact-name`/`--all`; `--export-dir` on
  `run`/`resume`; additive result keys on all three commands.
- `copy_artifact` function registered with full ADR 009 metadata.
- 176 tests pass; ruff clean.

One ADR text correction applied at freeze: Decision §1 removed the phrase "symmetric to unresolved
`param.`/`output.` references" because the mechanisms differ — `param.`/`output.` unresolved
references raise `StateLoadParameterError` (engine-level), while `artifact_not_found` is caught at
the action level and returned as a node error value. The Implementation Notes already described this
correctly; the Decision text was tightened to match.

Feature branch merged into `development`; ADR 011 frozen as Accepted.

## Decisions
- The corrected Decision §1 wording is not a reversal: the observable behaviour (node fails on
  unknown artifact name) is unchanged. The correction removes a misleading mechanism analogy.
- The architecture overview gains a new "Artifacts and deliverables" subsection under State, as the
  contract is now stable enough to document.

## Next steps
1. Consider an `examples/` workflow that declares a deliverable, as an operator-facing template
   (flagged in the implementation session; no ADR required, authoring work only).

## References
- Feature branch merged: `feature/adr_011-artifact-addressing-and-export`
- ADR: `docs/adr/adr-011-artifact-addressing-and-export.md`
