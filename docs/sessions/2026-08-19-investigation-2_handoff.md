# Session note

## Type
investigation

## Goal
Run the final pre-release audit of `development` after the fix sessions that closed the findings of
`2026-08-18-investigation-1` and `2026-08-19-investigation-1`, and state whether phase 1 can be
released (merge `development` into `main`, tag `v0.1.0`).

## Completion criteria
1. Tests, linter and formatter are run on `development` and the outcome recorded.
2. Every finding of the two previous audits is re-checked against the current code and documents and
   marked closed, deliberately deferred, or still open.
3. The code and documentation changed since the previous audit (`copy_file` target semantics, action
   metadata, README, overview, registries) are re-audited for new inconsistencies.
4. Every README command sequence is executed once more from a directory outside the repository.
5. A release verdict is recorded: either "no blocking finding" or the list of blocking findings.

## Scope boundaries
- Investigation only: no code or documentation change other than this note.
- The release itself (merge and tag) is not performed here; it is the next step if the verdict allows.

## Status
completed

## Result
Verification on `development` at `35bb59e`: `uv run pytest` — 249 passed; `uv run ruff check .` —
clean; `uv run ruff format --check .` — 194 files already formatted. Working tree clean;
`development` equals `origin/development`; `main` is 178 commits behind with nothing of its own; no
tag exists; `pyproject.toml` version is `0.1.0`. Merged branches are deleted locally and remotely.

### Previous findings re-checked
- `2026-08-19-investigation-1`: A.1, A.2 (documentation and code), C.1, C.2, D.1–D.5, E.1–E.6 and
  the three open questions are closed (fix sessions `documentation-3`, `documentation-4`,
  `implementation-2`, `implementation-3`); E.7 still holds. Residuals: B.9 is only half closed (see
  finding 2 below); D.2 left "frozen as Accepted" change-log entries missing in ADR 002, 005, 007;
  E.2 left one legacy heading deviation (`2026-08-11-implementation-1`, `## Next steps for the next
  session` plus non-template sections).
- `2026-08-18-investigation-1`: findings 2 (ADR 011), 3 (`pretty_table_no_data`), 5 (`session_id`,
  BOM, CSV rows), 7 (examples and fixture) are closed; finding 6 is closed by removing the `resume`
  flags under ADR 012 with interactive input deferred to phase 2; open question 1 (hard cap default)
  is deferred to the open note `2026-08-19-hard-node-cap-scoping.md`.

### New findings
Candidate blocker (contract defect, small fix):
1. A failed run pollutes stdout under `--json`: `engine.py:234,257,321` `print("Engine stop: ...")`
   to stdout before the CLI renders the JSON response, so `run --json`/`resume --json` of a failed
   workflow is not parseable JSON (reproduced: `flatten-copy-tree` with a non-existent `target_dir`,
   exit 3, `json.load` fails on stdout). ADR 007 promises `--json` for automation; the failure path is
   the one automation most needs to parse. The message is already carried by the `errors` field and
   the `workflow_failed` session event, so the prints can be dropped (or moved to stderr); no test
   depends on them.

Non-blocking, code or templates:
2. `docs/architecture/overview.md:233-235` states that `set-limit` refuses to lower the limit below
   the current node count; `engine.py:514-518` refuses any value below the current *limit* and never
   reads `nodes_visited` (B.9 wording is wrong, not the code; no ADR pins either rule).
3. Both templates end with an unconditional `{"stop": true}` after the table-writing node, so a
   failed deliverable write (`pretty_table_write_error`) completes the run with exit 0, an empty
   `artifacts` map and a `deliverable_missing` event. Consistent with ADR 011 ("delivery problems never
   annul completed work") and with errors-as-values, but an operator reading exit 0 as "CSV produced"
   is misled; an `errors` failure transition before `stop` in `examples/*.json` would surface it.
4. README:79-81 "the first copy fails … and the run stops" is imprecise: `COPY_FILE` carries only an
   unconditional transition, so the run continues to `COLLECT_ROW` and fails there with
   `StateLoadParameterError` on `param.copied_path`; the `target_folder_not_found` code is visible only
   in `errors.COPY_FILE`. Same fix class as finding 3 (an `errors` transition in the template).
5. README:52 "runs from any working directory with `uv run workflow-engine`" needs the repo venv on
   `PATH` or `uv run --project <repo>`; from an unrelated directory `uv run` reports "program not
   found". Missing precondition.
6. `help-component --component-type codecs --component-name Path` is not found (exit 4); only the
   long name `pathlib._local.Path` resolves there, while `--input NAME:Path=` accepts the bare name
   (README:88-90 says the bare name "also resolves"). Belongs to the open note
   `2026-08-18-adr012-deferred-questions.md`.
7. `help-component` via a launcher script that imports the user module reports `Source: core` for the
   user's function; `Source: external` appears only on the `external_modules` path (README:197-198).
8. `run --export-dir --json` reports `event_code: artifacts_exported` but no destination or exported
   list in `data`; the destination is only in the session event.
9. Windows `MAX_PATH`: a session created under a very long working directory fails its artifact write
   with `pretty_table_write_error` (`[Errno 2]`); environmental, worth a README note at most.

Non-blocking, documentation and process:
10. Overview imprecisions: overview.md:66 guard name as error code holds only for the `validators`
    expansion (routing guards that all fail yield `no_transition_matched`, `engine.py:30,144`);
    overview.md:41 "an error is a value" omits `WorkflowRuntimeError` escaping the action to the
    engine (`engine.py:256-271`); overview.md:58-59 omits the `attempts`-to-another-node case and the
    default `max_attempts=3`; overview.md:265-266 omits guard `kind` and codec `python_type` detail
    keys; overview.md:216-217 an explicit `--config` path is also auto-created; overview.md:146-148
    omits the declared-type agreement check and the `workflow_setup_failed`/`missing_inputs` event.
    `CLAUDE.md` Architecture repeats the pre-B.2 wording "never the state directly".
11. `docs/rules/implementation-rules.md:51,58` duplicate `## 10.` numbering (already a next step in
    three session notes, never done); `docs/rules/README.md:11` wrong relative path and incomplete
    architecture routing; ADR registry `Depends on` vs file "Related ADRs" diverge for 002, 004, 005;
    `tests/test_json_storage.py:204-222` Cyrillic fixture strings are the only non-English text in
    tracked files (test data, defensible, but avoidable); `.gitignore` carries a BOM; session-note H1
    wording varies (template does not prescribe it).

### Verdict
No blocking finding against the phase 1 gate as defined in `2026-08-18-architecture-5`. Finding 1 is
the only contract-level defect and is recommended to be fixed before the tag because it breaks the
`--json` automation promise on the failure path and costs three lines; the user decides whether the
tag waits for it.

## Decisions
1. Nothing is fixed in this session; findings are the deliverable.
2. Finding 1 is classified as a candidate blocker, findings 2–11 as post-tag follow-ups grouped at the
   user's discretion (templates/README in one `fix/`+`docs/` pair, overview nits in one `docs/`).

## Open questions
1. Does the `v0.1.0` tag wait for the finding 1 fix (`fix/` branch, ~3 lines, then re-tag audit not
   needed) or is it released as-is with the defect recorded?

## Next steps
1. Decide open question 1; if fixing, open `fix/engine-stop-stdout` (drop or redirect the three
   `print` calls, add a `--json` failed-run parse test).
2. Merge `development` into `main`, tag `v0.1.0`, push (phase 1 gate item 4).
3. Post-tag: template hardening (`errors` transition before `stop`, findings 3–4) with the README
   wording (findings 4–5); overview and rules corrections (findings 2, 10, 11).

## References
- Branch: `docs/phase1-final-audit`
- Previous audits: `2026-08-18-investigation-1_handoff.md`, `2026-08-19-investigation-1_handoff.md`
- Phase 1 completion gate: `2026-08-18-architecture-5_handoff.md`
- Documents audited: `docs/architecture/overview.md`, `README.md`, `docs/adr/*`, the three registries,
  `docs/rules/*`, `docs/processes/git-workflow.md`, `CLAUDE.md`, `AGENTS.md`,
  `.github/copilot-instructions.md`, `examples/*.json`
