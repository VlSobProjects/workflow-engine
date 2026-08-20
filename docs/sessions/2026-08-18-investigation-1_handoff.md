# Session note

## Type
investigation

## Goal
Dogfood the recursive-folder-to-CSV scenario as an operator-engineer end to end (edit a workflow,
create a session, run it, retrieve the result) to record real usability findings and decide which
belong to a future artifacts ADR and which to a standalone bug-fix session.

## Completion criteria
1. A real operator run of the scan-to-CSV workflow is performed against a folder outside the
   repository, with commands and observed outcomes recorded as facts.
2. The artifact-retrieval gap is confirmed or refuted against the running app (can a workflow surface
   or export the produced CSV, e.g. via `copy_file`).
3. The empty-folder crash hypothesis in `dict_list_to_pretty_table` is confirmed or refuted on a real
   run.
4. The hard-cap (ADR 010) behaviour on a large folder is observed with concrete numbers.
5. Findings are split into: artifacts gap (candidate ADR), standalone bugs (bug-fix session), and
   template tuning notes (for the later examples session). No production code is changed here.

## Scope boundaries
- Investigation only: run the shipped CLI, observe, record. No engine, function, or example changes.
- No new ADR is opened in this session; it only decides whether one is warranted.
- The scratch operator folder lives outside the repository so the working tree stays clean.

## Status
completed

## Result
The recursive folder-to-CSV scenario runs end to end as an operator: editing the workflow JSON,
`init-new-session` from the operator folder, `resume` to execute, and `show-state` to inspect the
result. Running from a folder creates `<folder>/.workflow-engine/` with the config, `sessions/` and
`json-storage/`; the config is operator-editable and drove the safety-cap recovery below. All facts
below were observed on the installed CLI against a scratch tree outside the repository.

Confirmed findings:
1. Scenario is useful and correct: the CSV carries exactly the chosen columns
   (Path, Size, MIME, Modified, MD5) for every file, and empty subfolders are skipped.
2. Artifact retrieval is a real gap (candidate for a dedicated ADR):
   - `run`/`resume` output omits the artifact location (only `work_dir` is present); the operator must
     call `show-state`, which exposes `artifacts_path` and the `artifacts` map, and then join them by
     hand to reach the file. The concrete file path is never returned directly.
   - The artifact is locked under `<session>/artifacts/...`; `dict_list_to_pretty_table` rejects an
     `artifact_path` outside `work_dir/artifacts`, so it cannot write straight into the operator folder.
   - A node cannot reference an artifact's real path: no registered function exposes `state.artifacts`,
     and the natural attempt (`copy_file` with `path_source: output.WRITE_TABLE`) fails because the
     node output text is `pretty_table_created`, not a path. Exporting the CSV from within a workflow
     is impossible today.
3. Empty-root bug (candidate for a standalone bug-fix): scanning a root with no files fails with an
   opaque `list index out of range` (exit 3) from `dict_list_to_pretty_table` indexing `dict_list[0]`
   on an empty list, instead of the `pretty_table_no_data` error code the same function already returns
   for the non-list case.
4. ADR 010 safety cap validated as an operator flow: with `hard_max_nodes_visited` lowered in the
   config, the run pauses with `workflow_paused_safety_limit` (exit 2, clear message); raising the cap
   in the config and resuming completes the run (exit 0). The config-edit recovery works as designed.
   Note: the default cap of 1000 is low for real folder scans (~330 tree entries trip it).
5. Minor findings: `init-new-session` JSON returns a top-level `session_id: null` (the id is only in
   `data.session_id` and `message`), inconsistent with `resume`/`show-state`; a UTF-8 BOM breaks both
   config and workflow loading (`json.load`), which matters for the mechanical-replace flow because
   `Set-Content -Encoding utf8` on Windows PowerShell 5.1 writes a BOM (use a BOM-free write instead);
   the prettytable CSV has blank lines between rows on Windows (cosmetic).
6. Blocking CLI bug for a parameterised scan root: `resume --param-name --param-value --write-mode`
   crashes with an unhandled `ValueError: '<MODE>' is not a valid WriteParamMode` (exit 1, traceback).
   `cli/use_cases.py` builds the mode as `WriteParamMode(args.write_mode)` (by value) while the parser
   restricts `--write-mode` to enum names (`choices=[mode.name ...]`) and the guard checks by name, so
   parameter injection via `resume` cannot work for any mode. The fix is `WriteParamMode[args.write_mode]`.
   Consequence: a CLI-replaceable folder parameter is impossible today; even once fixed it needs a
   placeholder start node plus `--input` (because `_output_node` only builds an output when `--input`
   or `--error-code` is present) and the two-step `init` + `resume`, never a one-shot `run`.
7. The `examples/` folder is stale and coupled to the tests. Four files use a defunct questionnaire
   schema the engine cannot load (`loop-start-flow.json`, `loop-install-flow.json`,
   `test-workflow-1.json`, `state-empty.json`); `simple_workflow.json` uses the current schema but
   carries personal absolute Windows paths, and it also doubles as a test fixture: `conftest.examples_dir`
   feeds it to `test_engine.py` and `test_json_storage.py`, and `test_simple_workflow` asserts its node
   structure (`visit_counters["NODE_1"] == 1`, `["NODE_3"] == 1`). So the folder cannot be cleaned
   without either decoupling the tests (moving a fixture into `tests/`) or replacing the file content
   with a portable workflow of the same node shape.

## Decisions
1. The artifact access and extraction gap (finding 2) is architectural and warrants a dedicated ADR:
   node/function access to artifacts plus an export or externally-addressable output mechanism.
2. The empty-root failure (finding 3) is a self-contained defect fixed in a standalone bug-fix session,
   folded into the artifacts ADR only if the fix turns out to depend on it.
3. Example JSON files are assets, not code, so the `examples/` asset cleanup is done in this session:
   the four defunct questionnaire-schema files are removed and two validated templates are added
   (`folder-inventory-to-csv.json` for the recursive scan, `flatten-copy-tree.json` for the recursive
   copy), each carrying a placeholder root token for mechanical CLI replacement until workflow
   templating exists, and each verified by a real run.
4. Only the code-touching part of the cleanup is deferred to an implementation session (approach B):
   `simple_workflow.json` is kept as-is because it is a test fixture (`test_engine.py`,
   `test_json_storage.py` via `conftest.examples_dir`, with `test_simple_workflow` asserting its node
   shape); replacing its personal-path content with a portable workflow of the same shape, or moving
   the fixture into `tests/`, is left to that session. The run/retrieve how-to for the templates in the
   top-level `README.md` is left to the same session.

## Open questions
1. Should the default `hard_max_nodes_visited` stay at 1000, or is a higher default (or a documented
   per-scan soft-limit checkpoint pattern) better for folder-scan workloads?
2. Does the minor-findings bucket (finding 5) go into the same bug-fix session or its own?

## Next steps
1. Open a Draft ADR for artifact access and extraction, capturing finding 2 as its context.
2. Open a standalone bug-fix session for the empty-root failure (finding 3) and the CLI param-mode
   crash (finding 6), and decide the home of the minor findings (finding 5).
3. Open an implementation session for the code-touching remainder of decision 4: replace the
   personal-path content of `simple_workflow.json` (or move the fixture into `tests/`), and add the
   template run/retrieve how-to to the top-level `README.md`.
4. Remove the scratch operator folder used for the experiment (outside the repository) when no longer
   needed for inspection.

## References
- Related: ADR 006 (data flow, artifacts), ADR 010 (safety cap).
- Branch: `docs/operator-scan-experiment`