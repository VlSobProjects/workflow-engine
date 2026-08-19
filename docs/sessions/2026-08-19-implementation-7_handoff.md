# Session note

## Type
implementation

## Goal
Make a `FunctionRuntimeError` readable in the JSON payload: name the function and the parameters it
was actually given, once, without the injected state view.

## Completion criteria
1. The `errors` entry of a run that failed inside a registered function contains no
   `StateReadOnlyView` repr and no `output` entry.
2. The function name and its parameters appear once in the message, not twice.
3. No message ends in `No message` because the failure text was put in the parameters slot.
4. `uv run pytest` and `uv run ruff check .` pass, and the behaviour is covered by tests.

## Scope boundaries
- Only `FunctionRuntimeError` and the two places that raise it. `FunctionConfigurationError` keeps its
  message: it is raised while a node is built, before any state is injected, so it carries no state.
- No change to which exception type is raised, to error codes, or to the result shape.
- Items 3, 4, 6, 7 and 8 of the shortlist belong to their own sessions.

## Status
completed

## Result
Verified: `uv run pytest` — 265 passed; `uv run ruff check .` — clean; `uv run ruff format --check .`
— 202 files already formatted.

The `errors` entry of a run that fails on a missing source file went from a paragraph containing a
full `StateReadOnlyView` repr, the function name twice and a trailing `No message`, to one line:
`Function runtime error in 'copy_file': path_source: Argument <path> - validation 'file exists'
failed.`

Three causes, each fixed where it lives:
1. `RegisteredFunctionExecutor.execute` reported the resolved parameter dict, which the engine has
   already extended with `output` and the read-only state view. It now reports what the signature
   filter keeps — the same filter that decides what the function is actually called with.
2. The failure was wrapped in a second `FunctionRuntimeError` about the same function, repeating its
   name and parameters. An inner `FunctionRuntimeError` naming the same function is now re-raised.
3. `functions_validators._check_args` put the validation failures into the `parameters` slot and left
   the message empty, which is where the trailing `No message` came from. They are the message now.
`FunctionRuntimeError` also drops the `with parameters '...'` clause when there are none.

## Decisions
1. Cause 3 was not named in the shortlist, which lists only the parameter dump. It is fixed here
   anyway: it is the second half of the same unreadable string, in the same call chain, and leaving
   it would have made the session's completion criteria unreachable.
2. `FunctionConfigurationError` keeps its message unchanged. It is raised while a node is built,
   before the engine injects anything, so its parameters are the operator's configuration and belong
   in the text.
3. An inner `FunctionRuntimeError` naming a *different* function is still wrapped: that is a nested
   call, and the outer function's identity is information, not noise.

## Open questions
None for this item.

## Next steps
1. Run `fix/help-component-resolution` (shortlist items 3 and 4).
2. Run `chore/repo-hygiene` (items 6, 7, 8).
3. Close the batch with a maintenance session: bump `pyproject.toml` to `0.1.1`, merge `development`
   into `main` and tag `v0.1.1`.
4. Outside this batch: `StopAction._execute` (`actions/action_nodes.py:229-231`) passes
   `lambda d: d.update(...)` as its parameter updater. `dict.update` returns `None`, so the executor
   takes its `parameters is None` branch and calls the function with no arguments at all: a `stop`
   node that declares `function_name` with `function_parameters` silently ignores them and skips
   `param.`/`output.` resolution. Found while reading this code, not fixed here, not on the shortlist.

## References
- Branch: `fix/function-error-message`
- Source: `2026-08-19-investigation-3_handoff.md` (item 5)
