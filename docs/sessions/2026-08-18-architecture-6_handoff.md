# 2026-08-18 architecture 6 — Accept ADR 012 workflow input parameters

## Type
architecture

## Goal
Review the ADR 012 implementation against the ADR requirements, merge the feature branch into
development, and freeze ADR 012 as Accepted.

## Completion criteria
- All 236 tests pass and ruff is clean on the feature branch.
- Context, Decision and Consequences in ADR 012 describe the delivered result.
- Freeze gate satisfied; ADR 012 status set to Accepted on development.
- ADR registry and session registry updated; architecture overview left as-is (already describes
  the input-parameter subsystem accurately).

## Scope boundaries
- ADR 012 conformance review, freeze, and the merge that carries it, plus the related registries.
- No new contract decisions.

## Status
completed

## Result
Implementation verified:
- `InputDeclaration` + `WorkflowModel.inputs` + `_validate_inputs` at build time.
- `resolve_codec_by_type_name` (full or unambiguous bare name) on the codec registry.
- `INPUTS_SET` operator event journaled with bound names and codec names (not values).
- Engine `set_inputs` / `get_inputs` and first-start required-input check (`workflow_setup_failed`,
  exit code `4`).
- Domain module `workflow_engine/inputs.py` for pure assignment parsing and codec decoding.
- `set-input` command and one-shot `run --input`.
- Uncontracted `resume` operator-output flags and their helpers removed.
- `folder-inventory-to-csv` and `flatten-copy-tree` examples migrated to declared `inputs` and
  `deliverables`.
- 236 tests passing, ruff clean.

Freeze gate: all four criteria met. Feature branch merged into development. ADR 012 status set to
Accepted; active branch field cleared.

## Decisions
- No changes to the ADR text were needed: the delivered result matches the Decision section.
- Architecture overview already contained the accurate "Input parameters (see ADR 012)" subsection
  (written during implementation); no update needed.

## Open questions
None.

## Next steps
1. Phase 1 completion gate: all twelve ADRs (001–012) are now Accepted. Assess whether phase 1 is
   satisfied or whether open architecture questions remain.
2. Decide the next session: phase 1 tagging / release prep, or a new architecture cycle.

## References
- Branch: `feature/adr_012-workflow-input-parameters` (merged)
- ADR: `docs/adr/adr-012-workflow-input-parameters.md` (Accepted)
- Preceding session: `2026-08-18-implementation-7_handoff.md`
