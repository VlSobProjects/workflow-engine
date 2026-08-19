# Session note

## Type
implementation

## Goal
Make the failure path of `run`/`resume` produce parseable output under `--json` by removing the
`Engine stop: ...` prints the engine writes to stdout (finding 1 of `2026-08-19-investigation-2`).

## Completion criteria
1. No engine code path writes to stdout; the three `print` calls in `engine.py` are gone.
2. A test runs a failing workflow through the CLI with `--json` and parses stdout as JSON.
3. `uv run pytest` and `uv run ruff check .` / `uv run ruff format --check .` pass.

## Scope boundaries
- The engine, the two run commands of the CLI and their tests. No change to the command surface, the
  presenters, the exit codes or the JSON field set.
- No stderr channel is introduced: it is not described by ADR 007 or the architecture overview.
- The two `print` calls in `json_storage.load_all_states` stay: that method is reachable from no
  command, and what to do with it is a separate question (see next steps).

## Status
completed

## Result
All three `print` calls are gone from `engine.py`; no engine code path writes to standard output.
Removing them alone would have lost information, so the run commands now keep the errors the engine
reports on its response:

- Node failed its guards (`engine.py:234`): the cause was already in `errors.<node_id>` through the
  state; unchanged.
- Current node not found in the workflow (`engine.py:321`): `message` and `data.current_node` name the
  cause; unchanged.
- `WorkflowRuntimeError` escaping an action (`engine.py:257`): the state records no node error, so
  `errors` was empty and the exception text existed only in the removed `print`. `run_workflow` and
  `resume_workflow` (`cli/use_cases.py`) now merge `PresentResponse.errors` into the command result,
  state values winning on a shared key.

`docs/architecture/overview.md` records both properties in the CLI contract section.

Two tests in `tests/test_cli_contract.py`: a failed run under `--json` whose stdout is parsed as a
whole (it fails if any `print` returns), and a run ending in an exception whose cause must appear in
`errors`.

Verification: `uv run pytest` — 251 passed; `uv run ruff check .` — clean; `uv run ruff format
--check .` — 195 files already formatted.

## Decisions
1. The prints are removed, not redirected to stderr: the CLI contract has no stderr channel, and
   introducing one would need ADR 007, which is frozen.
2. The command result is the single carrier of a failure cause, so the engine response errors are
   merged into it instead of being dropped.

## Open questions
None.

## Next steps
1. Merge into `development`, register the session, then the phase 1 tag (`v0.1.0`).
2. New finding, post-tag: `FunctionRuntimeError` builds its message from all function parameters
   including the injected `state` and `output`, so a single failure now shows the whole
   `StateReadOnlyView` repr inside `errors`. It was equally unreadable on stdout before; it is now
   part of the JSON payload and should be reduced to the declared parameters.
3. New finding, post-tag: `Storage.load_all_workflows` and `StateSource.load_all_states` are called by
   no command and no test, and `JsonStorage.load_all_states` prints to stdout on a corrupt state file.
   Decide whether the pair is removed or given a caller and a proper error report.
4. The follow-ups of `2026-08-19-investigation-2` findings 2-11 stay as recorded there.

## References
- Branch: `fix/engine-stop-stdout`
- Audit finding: `2026-08-19-investigation-2_handoff.md`, finding 1
- Changed: `src/workflow_engine/engine.py`, `src/workflow_engine/cli/use_cases.py`,
  `tests/test_cli_contract.py`, `docs/architecture/overview.md`
