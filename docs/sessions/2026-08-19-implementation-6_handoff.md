# Session note

## Type
implementation

## Goal
Close the two CLI JSON contract gaps of the `v0.1.0` patch shortlist: a malformed command line must
never write to stdout and must honour `--json`, and a run or resume that exported deliverables must
report where they went.

## Completion criteria
1. A malformed command line writes its message and usage to stderr only, and exits `4`.
2. With `--json` on a malformed command line, stdout carries exactly one `CommandResult` document
   with `command_status: error`.
3. `run` and `resume` that performed the completion export carry the export destination and the
   exported map in `data`, additively as ADR 011 allows.
4. Both behaviours are covered by tests; `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- Items 3 to 8 of the shortlist belong to their own sessions.
- The `--help` path is correct as it is and is not touched.
- No change to exit codes, to the existing result keys, or to the session event journal.

## Status
completed

## Result
Both items of the shortlist are closed and verified: `uv run pytest` — 262 passed; `uv run ruff
check .` — clean; `uv run ruff format --check .` — 201 files already formatted.

1. `ArgumentParser.error` no longer writes and exits by itself: it raises `CommandLineError`, and the
   entry point writes the message and the usage to stderr. With `--json` on the command line stdout
   carries one `CommandResult` with `command_status: error` and the argparse text under
   `errors.command_line`. `--help` is untouched: it runs through `parser.exit`, and its stdout is the
   answer the operator asked for.
2. `export_deliverables_on_completion` returns a `DeliverableExport` instead of nothing; the engine
   keeps the outcome of the last run it started and exposes it as `get_last_export()`. `run` and
   `resume` add `data.export` with `destination` and the exported map. The key is absent when no
   completion export ran at all.

## Decisions
1. `CommandResult.command` becomes `CommandName | None`. A command line too malformed to name a
   command still answers in JSON, with `command: null`, rather than inventing a command name.
2. The command a malformed call meant is read from the first positional token of `argv`, and `--json`
   is detected by its presence there. Both are safe because the top-level parser takes no options of
   its own: the first non-flag token is always the command.
3. The last completion export is engine state, not session runtime state: `SessionRuntime` is frozen,
   and the value describes one run rather than the session. It is reset at the start of every
   `start_workflow`.
4. `data.export` reports the destination and the exported map only. Missing and failed deliverables
   keep their existing session events; duplicating them in the result was left out of scope.

## Open questions
None.

## Next steps
1. Run `fix/function-error-message` (shortlist item 5).
2. Run `fix/help-component-resolution` (items 3 and 4); item 4 is decided: `source` states where a
   component comes from, so it is derived from the registering module and README needs no change.
3. Run `chore/repo-hygiene` (items 6, 7, 8).
4. Close the batch with a maintenance session: bump `pyproject.toml` to `0.1.1`, merge `development`
   into `main` and tag `v0.1.1`.

## References
- Branch: `fix/cli-json-contract-gaps`
- Source: `2026-08-19-investigation-3_handoff.md` (items 1 and 2)
- ADR 007 (CLI contract), ADR 011 (additive result keys)
