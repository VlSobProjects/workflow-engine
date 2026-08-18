# 2026-08-18 implementation 7 — ADR 012 workflow input parameters

## Type
implementation

## Goal
Implement ADR 012: declared workflow `inputs`, typed pre-run binding via `set-input` and `run --input`,
setup-time enforcement, and removal of the uncontracted `resume` operator-output flags.

## Completion criteria
- `inputs` declaration on the workflow definition, validated at build time (name charset, uniqueness,
  registered codec type).
- `set-input` command and one-shot `run --input`, decoding typed values through codecs and journaling
  an `inputs_set` operator event.
- Binding rejected after the run has started; unbound `required` inputs fail the first start with exit
  code `4`.
- The nine `resume` operator-output flags and their `_output_node`/`_get_parameters`/`_get_artifacts`
  helpers removed.
- `uv run ruff check .` clean and `uv run pytest` green, including a parameterized folder-inventory
  e2e that exports through `--export-dir`.

## Scope boundaries
- No mid-run interactive input (phase-2, ADR 007 §4); `WriteParamMode`/`get_all_modes_help` kept for
  the engine-internal write modes and that future surface.
- No new help-contract component type: inputs surface via `run`/`resume`/`show-state` result data,
  mirroring `deliverables`.
- No repo-wide reformatting: only files changed by this work were formatted.

## Status
completed

## Result
Delivered against every criterion. `InputDeclaration` + `WorkflowModel.inputs` + `_validate_inputs`;
`resolve_codec_by_type_name` (full or unambiguous bare name) on the codec registry; `INPUTS_SET`
operator event (added to `OPERATOR_CODES` and the PAUSED status arm); engine `set_inputs`/`get_inputs`
and a first-start required-input check; a domain module `workflow_engine/inputs.py` for pure assignment
parsing and codec decoding; the `set-input` command and `run --input`; removal of the `resume` flags.
The shipped `folder-inventory-to-csv` and `flatten-copy-tree` examples were migrated to declared
`inputs` (queue seeding restructured to a resolvable top-level `param.<name>` reference) with a
`deliverables` block. Six new test files (schema, assignment parsing, binding matrix, required-start,
CLI, e2e); full suite 236 passing, ruff clean.

## Decisions
- Required-unbound start error journals `workflow_setup_failed` then raises `WorkflowInputError`, which
  the CLI maps to exit `4`; the return-path node-build setup error keeps exit `3` (ADR 012 §5).
- The started-guard and first-start check key off the `workflow_started` journal event, not node
  counters (a run paused at an interactive first node has visited no node yet).
- Parsing/decoding live in `workflow_engine/inputs.py` (domain), not `cli/`, so the engine does not
  depend on the CLI. Recorded in the ADR 012 change log.
- The registered full codec name is Python-version dependent (`pathlib._local.Path` on 3.13);
  operators use the stable bare name (`Path`).

## Open questions
None.

## Next steps
1. Review the implementation against ADR 012.
2. Merge `feature/adr_012-workflow-input-parameters` into `development`; on `development` add this
   session's registry row and the ADR 012 registry status, and check the freeze gate.
3. Freeze ADR 012 as Accepted on `development`.

## References
- Branch: `feature/adr_012-workflow-input-parameters`
- ADR: `docs/adr/adr-012-workflow-input-parameters.md` (Implementing)
- Changed docs: `docs/architecture/overview.md` (public commands, input parameters subsection)
- Preceding session: `2026-08-18-architecture-5_handoff.md`
