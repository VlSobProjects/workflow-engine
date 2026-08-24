# Session note: 2026-08-24 implementation 1

## Type
`implementation`

## Goal
Implement ADR 020: the three output composition functions, the authored template file they render,
and the corrected inventory example that gives the operator a readable deliverable.

## Completion criteria
- `dict_list_to_grouped_tables`, `write_text_artifact` and `render_template_to_artifact` are
  registered core functions with ADR 009 documentation and unit tests.
- A template file resolves `${...}` references against the state; its path is absolute or relative
  to the workflow definition file.
- The `folder-inventory-to-csv` example writes the grouped document the operator asked for, covered
  end to end.
- The ADR body describes what was delivered, with every departure from the Draft recorded in its
  change log; `README.md`, the walkthrough and `docs/architecture/overview.md` match the delivered
  surface.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No document model, no renderer registry, no template language (ADR 020 alternatives A and D).
- No composed artifact names and no collection write: both stay in Leaves open with their triggers.
- The ADR 019 narrowing, the `llm` node and the atomic-write `fix/` session are other steps.
- The `refactor/` debts of the 2026-08-23 audit are not touched here.

## Status
`completed`

## Result
- Three functions in `actions/create_artifact_functions.py` over one shared write-and-register
  path; ten error codes, of which the existing-artifact cases keep the registration contract's own
  `artifact_overwritten` / `artifact_path_conflict`.
- `StateModel` records the directory of the workflow definition file when the session is created,
  and `StateReadOnlyView.resolve_authored_path` resolves an authored file against it; an absolute
  path is used as written, and a session without the record answers `template_path_unresolved`.
- `file_parent_folder` and `file_name` added to the file-info family, without which the example
  cannot group by folder.
- `folder-inventory-to-csv` now writes two deliverables over the same rows: the flat
  `file_scan_table` CSV and the `file_scan_report` document, a table per folder under its path.
- 14 unit tests plus two e2e assertions; `uv run pytest` 473 passed, `uv run ruff check .` clean,
  `uv run ruff format .` applied (3 files).
- Documentation carried in the same branch: the ADR body, the walkthrough, the scenario registry
  row, `README.md`, `docs/architecture/overview.md`.

## Decisions
1. **The build-time template check and the session snapshot are not delivered, and the ADR says so.**
   Both need the engine to know that a function parameter names a template file — the kind
   mechanism ADR 020 defers in Leaves open. A malformed placeholder is therefore the routable
   function error `template_malformed`, and the definition directory is recorded in the state
   rather than a copy of the template in the session. Recorded as an amendment in the ADR change
   log, not as a quiet rewrite (`adr-rules.md` §5).
2. **The definition directory lives in the state, not in the session record.** The state is what
   holds everything a resume needs (ADR 006), the field is additive, and a session that predates it
   simply has none — no session record changes shape and ADR 004 is untouched.
3. **The grouped document is a second deliverable, not a replacement.** A markup table syntax stays
   valid inside a section and is not valid for the composed file as a whole, so the machine-readable
   flat table stays and the reader gets the composed one. The example ships both, which is also the
   honest answer to the operator's report.
4. **Two file-info functions were added** (`file_parent_folder`, `file_name`) beyond the three the
   ADR names: grouping by folder is unexpressible without a folder column. They belong to the
   existing file-info family, not to the output family, and are recorded in the ADR change log.
5. **A template file with no `$` is written as it stands** rather than being resolved as a
   whole-value reference: a file is text, not a configuration value.

## Open questions
None. The two Leaves-open items keep their triggers: the function-parameter template kind
(roadmap step 11) and writing a collection as an artifact (the `workflow-authoring` build).

## Next steps
1. Merge this branch into `development` and set ADR 020 to Accepted there, once the freeze gate is
   checked: the walkthrough and the scenario registry list the ADR, which they now do.
2. Roadmap step 8: ADR 014 into Implementing — its §7 now points at the delivered loader.
3. The `fix/` session for the atomic state write and the session lock, at any pause.

## References
- Branch: `feature/adr_020-output-composition-functions`.
- Code: `actions/create_artifact_functions.py`, `actions/file_info_functions.py`,
  `models/state.py`, `bootstrap/session_factory.py`, `engine.py`.
- Tests: new `tests/test_adr020_output_functions.py`, `tests/test_examples_templates.py`,
  `tests/test_adr012_e2e_scan.py`.
- Documents: `docs/adr/adr-020-output-composition-functions.md`,
  `docs/adr/adr-014-llm-node-and-provider-adapter.md` (§7, the loader now exists),
  `examples/folder-inventory-to-csv.json` and `.md`, `docs/architecture/scenarios/README.md`,
  `docs/architecture/scenarios/workflow-authoring.md`, the two notes and their registry,
  `README.md`, `docs/architecture/overview.md`.
- Related ADRs: ADR 020 (Implementing), ADR 016, ADR 011, ADR 006, ADR 009.
