# Session note

## Type
implementation

## Goal
Remove the silent data loss behind `copy_file`: make the meaning of the target path an explicit
choice of the workflow author instead of a value derived from the state of the file system
(audit finding A.2, code part).

## Completion criteria
1. `copy_file` treats `path_target` only as the full path of the copy: an existing folder and a
   missing parent folder are refused with their own error codes, and no parent folder is created
   implicitly.
2. A separate `copy_file_to_folder` copies into an existing folder under the source file name and
   refuses a missing folder with its own error code.
3. Both functions document every error code they can return in their operator help docstring.
4. The unreachable `file_not_found` branch of `copy_file` is removed.
5. `examples/flatten-copy-tree.json` and the copy-tree e2e use `copy_file_to_folder`; copying a tree
   into a non-existent target folder no longer reports success.
6. Tests cover: the folder target refused by `copy_file`, the missing parent refused by `copy_file`,
   the missing folder refused by `copy_file_to_folder`, and two files copied into one folder landing
   as two distinct files.
7. `uv run pytest` and `uv run ruff check .` pass from the command line.

## Scope boundaries
- Only the target-path semantics of file copying. `path_source` validation keeps its current
  mechanism (`file_exists_arg_validator`, a raising decorator) and its current behaviour.
- No general error-code taxonomy and no guard-level routing of runtime errors; that is a separate
  future decision by the user.
- No ADR: the change corrects a component defect, it does not alter an architectural decision. The
  ADR 009 change log keeps its record of the folder mode as delivered history.
- No release action (branch deletion, merge into `main`, tag).

## Status
completed

## Result
All seven completion criteria are met. `uv run pytest` — 249 passed (241 before, 8 added);
`uv run ruff check .` — clean; `uv run ruff format --check .` — 191 files already formatted.

`copy_file` now treats `path_target` only as the full path of the copy and never derives its meaning
from the file system: an existing folder is refused with `target_is_folder` and a message naming
`copy_file_to_folder`, a missing parent folder is refused with `target_folder_not_found`, and the
implicit `mkdir(parents=True)` is gone. `copy_file_to_folder` copies into an existing folder under the
source file name and refuses a missing folder with `target_folder_not_found`. Both document every
error code in their operator help docstring, following `dict_list_to_pretty_table`; the shared copy
and its `copy_failed` mapping live in a private `_copy` helper.

Verified outside the test suite on the shipped example. With a non-existent `target_dir`,
`flatten-copy-tree` now stops at the first copy: exit code `3`, `workflow_status: failed`,
`COPY_FILE` error `target_folder_not_found`, and nothing created on disk — previously the run
reported success while every source file overwrote one file named like the directory. With the
directory created, the same command completes with exit `0`, both source files land as distinct
files, and `copy_report.csv` carries one row per source with its own copied path and MD5.

## Decisions
1. Two functions rather than a mode flag on one (`copy_file` / `copy_file_to_folder`). The workflow
   author states the intent in the configuration, and `help-component` shows each intent with its own
   description and parameters. The rejected alternative, a `target_is_folder` flag, keeps one
   component but restores a silent default: a forgotten flag again decides the semantics.
2. Both new refusals are `ActionNodeOutput` error codes, not raising validators, matching the
   architecture's "errors are values inside the result". `path_source` keeps its raising
   `file_exists_arg_validator`: the engine turns `FunctionRuntimeError` into a failed run with an
   operator-readable message, which is sufficient until error codes are attached to runtime errors
   and can be routed by guards (a separate future decision by the user).
3. The unreachable `file_not_found` branch of `copy_file` was removed. `_reg`
   (`registry/function_registry.py:130`) wraps the registered callable in its decorators, so
   `file_exists_arg_validator` raises before the function body ever runs.
4. `tests/fixtures/simple_workflow.py` now creates `copy1`, `copy2` and `copy3` before the run. The
   fixture relied on the implicit parent creation that this session removed; the node shape and the
   guard behaviour the engine tests assert are unchanged.
5. ADR 009's change log keeps its statement that `copy_file` accepts an existing folder: it records
   what was delivered under that ADR and is frozen history, not the current contract.

## Open questions
1. Should runtime errors raised by argument validators carry their own error codes so guards can
   route them, instead of failing the run? Raised by the user during this session and deliberately
   left out of scope.

## Next steps
1. Delete the merged branches (audit finding E.6).
2. Merge `development` into `main` and tag `v0.1.0` (phase 1 completion gate item 4).
3. Correct the duplicate `## 10` section numbering in `docs/rules/implementation-rules.md`.

## References
- Branch: `fix/copy-file-target-semantics`
- Source: `docs/sessions/2026-08-19-investigation-1_handoff.md`, finding A.2 (code part)
- Rule decision on this finding class: `docs/sessions/2026-08-19-documentation-4_handoff.md`
- Files changed: `src/workflow_engine/actions/base_functions.py`, `tests/test_base_functions.py`,
  `tests/fixtures/simple_workflow.py`, `tests/test_adr009_e2e_copy_tree.py`,
  `examples/flatten-copy-tree.json`, `README.md`
