# Session note

## Type
implementation

## Goal
Make the two shipped templates fail visibly when the deliverable is not produced, closing findings 3
and 4 of `2026-08-19-investigation-2`.

## Completion criteria
1. Both templates fail the node under the error code the action returned instead of ending the run
   with exit 0 and no artifact.
2. `flatten-copy-tree` fails at `COPY_FILE` under the copy error code instead of continuing to
   `COLLECT_ROW` and dying there on an unset parameter.
3. The README statements about both templates match what the templates now do.
4. Both templates are covered end to end through the CLI, on their success path and on their failure
   path.
5. `uv run pytest` and `uv run ruff check .` / `uv run ruff format --check .` pass.

## Scope boundaries
- `examples/*.json`, the README sections about them, and their new test file. No engine, action or
  CLI change.
- Finding 5 (the `uv run` precondition in README:52) and findings 2, 6-11 stay for their own sessions.

## Status
completed

## Result
Both templates now carry a failure transition before the transition that ends the run:

- `WRITE_TABLE` / `WRITE_REPORT` fail under `pretty_table_no_data`, `pretty_table_artifact_exists` or
  `pretty_table_write_error`, keeping the code the action produced. A run that writes no CSV ends with
  exit code 3 and the code in `errors`, instead of exit code 0 with an empty `artifacts` map.
- `COPY_FILE` in `flatten-copy-tree` fails under `target_folder_not_found` or `copy_failed`. Before,
  the run walked on to `COLLECT_ROW` and died there with a `StateLoadParameterError` on the parameter
  the failed copy never wrote, which is not what the README described.

`README.md` states the shared rule once for both templates, names the empty-tree outcome of
`folder-inventory-to-csv`, and corrects the `flatten-copy-tree` paragraph to name the failing node,
the field the code appears in, and the `copy_failed` case.

`tests/test_examples_templates.py` covers each template end to end through the CLI on its success
path and on its failure path. Both failure tests were checked against the previous templates and fail
there, so they hold the change rather than restate it.

Verification: `uv run pytest` — 255 passed; `uv run ruff check .` — clean; `uv run ruff format
--check .` — 197 files already formatted.

## Decisions
1. An empty tree is a failed run, not a quiet success: the template declares a deliverable, so a run
   that produces no file did not reach its goal. The error code separates it from a write failure.
2. A single file that cannot be copied fails the whole run: a copy report that silently omits files is
   worse than a run that stops with a code.
3. The examples are treated as shipped artifacts and are tested as such; the README claim of two
   validated templates now has a test behind it.

## Open questions
None.

## Next steps
1. Merge into `development` and register the session.
2. Remaining audit follow-ups: finding 5 (the `uv run` precondition in README:52), findings 2 and 10-11
   (overview and rules corrections), findings 6-9 as recorded in `2026-08-19-investigation-2`.
3. Phase 1 tag `v0.1.0`.

## References
- Branch: `fix/template-failure-transitions`
- Audit findings: `2026-08-19-investigation-2_handoff.md`, findings 3 and 4
- Changed: `examples/flatten-copy-tree.json`, `examples/folder-inventory-to-csv.json`, `README.md`,
  `tests/test_examples_templates.py`
