# Session note

## Type
implementation

## Goal
Stop a successful run from reporting errors: `errors` must carry only what actually failed, so a
caller can read a non-empty map as a failure.

## Completion criteria
1. `run`/`resume` of a workflow that completes report an empty `errors` map.
2. A failing run still reports its cause, unchanged.
3. Both are covered by tests, at the engine response and at the command result.
4. `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- Only the default value of `PresentResponse.errors`. No change to what any response reports when it
  does report an error, to exit codes, or to `_with_engine_errors`.

## Status
completed

## Result
Verified: `uv run pytest` — 276 passed; `uv run ruff check .` — clean; `uv run ruff format --check .`
— 207 files already formatted. Checked against a real run: a completed `run --json` now answers
`errors: {}`, a failing one still names its cause.

`PresentResponse.errors` was declared with `default_factory=def_errors`, a boilerplate `other_error`
catalogue meant for an interactive prompt. Seven of the eight `PresentResponse` constructions in the
engine set `errors` explicitly; the terminal success response is the one that does not, so it took
the default. The default is now `None`.

The leak reached the caller only after `2026-08-19-implementation-4` added `_with_engine_errors`,
which merges the engine response's errors into the command result so an exception escaping an action
still names its cause. That merge is correct; what it merged on the success path was not.

## Decisions
1. The fix is at the default, not at the one response that omitted `errors` and not at the CLI merge.
   The engine must not tell its direct callers something false either, and a default that has to be
   overridden in every single construction is a trap for the next response added.
2. `def_errors` is kept although it now has no caller. It states the shape an interactive action will
   pass explicitly in phase 2, and its docstring now says that it is deliberately not a default. This
   is an exception to implementation rules §3 recorded on purpose, so a later hygiene pass does not
   have to re-derive it.
3. `docs/architecture/overview.md` gains the invariant, because it is what automation reads the field
   for. `README.md` needs no change: it mentions `errors` only in two worked failure examples, both
   still accurate.

## Open questions
None.

## Next steps
1. Re-point the `v0.1.0` tag once more, now that `fix/stop-action-parameters` and this session landed
   after the last move: merge `development` into `main`, move the annotated tag, force-push it.
2. Unchanged from before: the release procedure is still unwritten and stays with
   `docs/architecture/notes/2026-08-19-installation-and-distribution.md`. Once a GitHub Release or a
   published package exists, the tag stops being movable.

## References
- Branch: `fix/successful-run-reports-errors`
- Found in: `2026-08-19-implementation-9_handoff.md` (next steps, item 1)
- Introduced by: `2026-08-19-implementation-4` (the `_with_engine_errors` merge)
