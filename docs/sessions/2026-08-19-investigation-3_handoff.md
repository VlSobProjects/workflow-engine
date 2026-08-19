# Session note

## Type
investigation

## Goal
Collect every defect that is still open after the `v0.1.0` tag and is worth fixing as a patch on that
line, each re-checked against the tagged code, with a proposed grouping into fix sessions.

## Completion criteria
1. Every candidate is reproduced or read in the code at `v0.1.0`, not carried over from an earlier note.
2. Each item states what is wrong, what it costs the caller, and what the fix touches.
3. Items deliberately not fixed are named as such, with the reason.
4. The list is grouped into sessions in a proposed order.

## Scope boundaries
- Investigation only: nothing is fixed here.
- The installation and distribution question stays in its architecture note
  (`2026-08-19-installation-and-distribution.md`); it is not a patch-level defect.
- Phase 2 scope (interactive input, retry and recovery) is out.

## Status
completed

## Result
Verified at the tag: `uv run pytest` — 255 passed; `uv run ruff check .` — clean; `uv run ruff format
--check .` — 199 files already formatted. `main`, `development` and `v0.1.0` all point at `8c164e3`
and are pushed.

### Contract defects, worth a patch

1. **A malformed command line writes help to stdout and never produces JSON.**
   `cli/main.py:26-30` overrides `ArgumentParser.error` to `print` the message and then
   `print_help()`, both to stdout, and exits `4`. With `--json` given, stdout holds usage text and
   stderr is empty, so a caller that parses stdout fails on the most common error of all — a wrong
   call. Same class as the `Engine stop:` defect closed in `2026-08-19-implementation-4`, which that
   session did not cover because it stayed inside the engine. Fix: send parser output to stderr, and
   decide whether `--json` should additionally produce a `CommandResult` with `command_status: error`.

2. **`run`/`resume` with `--export-dir` do not report where the files went.**
   The result carries `event_code: artifacts_exported` and `data.artifacts` with the paths inside the
   session sandbox, while the export destination and the exported map exist only in the session event
   in `state.json`. Automation that asked for an export cannot learn the destination from the
   response. Fix is additive, which ADR 011 explicitly allows: carry the destination and the exported
   map in `data`.

3. **`help-component` cannot resolve a codec by its bare name.**
   `help_contract/builder.py:83-85` reads `CODEC_REGISTRY` by exact key, so `--component-name Path`
   fails with exit `4` while `pathlib._local.Path` resolves. The input surface disagrees:
   `registry/type_registry.py:104-124` resolves a bare, unambiguous class name, which is what
   `--input NAME:Path=` and both shipped templates use, and what README documents. One resolution
   rule should serve both surfaces.

4. **`help-component` calls a user's component `core` when a launcher script registered it.**
   `source` is derived from the component loader report (`help_contract/builder.py:27-41`), so only
   the `external_modules` path is ever `external`. The launcher-script route that README recommends
   (README:173-193) registers by import, and the same function then reports `core`, contradicting
   README:218-219, which promises the field tells core from external. Fix is either to derive the
   source from the module a component actually comes from, or to redefine the field as "loaded
   through `external_modules`" and say so in README. This one needs a decision before code.

### Diagnostics, worth a patch

5. **`FunctionRuntimeError` puts the whole resolved parameter dict into its message.**
   `registry/function_registry.py:177-183` passes the resolved parameters to the exception, and
   `exceptions.py:86-89` interpolates them, so the injected `state` view and `output` land in the
   text — a full `StateReadOnlyView` repr with every parameter value inside a single `errors` entry.
   The nested message also repeats the inner error. It was equally unreadable before, but it was on
   stdout; since `2026-08-19-implementation-4` it is part of the JSON payload. Fix: build the message
   from the declared parameters only.

### Cleanup

6. **A storage API nobody calls, printing to stdout.** `StateSource.load_all_states`
   (`models/state.py:227-229`) and `Storage.load_all_workflows` (`storage/storage.py:13-14`) are
   reachable from no command and no test; `JsonStorage.load_all_states` (`json_storage.py:63-78`)
   prints to stdout on a corrupt or unreadable state file. Decide between removing the pair and giving
   it a caller with a proper error report.
7. **`.gitignore` starts with a UTF-8 BOM.** It is the only tracked file that does.
8. **The only non-English strings in tracked files** are the Cyrillic fixtures in
   `tests/test_json_storage.py:204,209,215`. The test's purpose is a non-ASCII round trip, which
   non-ASCII Latin text serves equally well without breaking the English rule.

### Deliberately not fixed
- The Windows path limit: an operating condition, documented in README by
  `2026-08-19-documentation-5`, not a defect of the engine.
- `set-limit` refusing any value below the current limit rather than below the nodes already visited:
  the behaviour is deliberate as written and now documented, and no ADR pins either rule. It is a
  design question, not a defect; it belongs to an architecture session if it is reopened at all.

## Decisions
1. The eight items are grouped into four sessions, smallest coupling first:
   `fix/cli-json-contract-gaps` (1, 2), `fix/help-component-resolution` (3, 4),
   `fix/function-error-message` (5), `chore/repo-hygiene` (6, 7, 8).
2. Item 4 is not started before its open question is answered; the other three sessions are
   independent of each other and of that answer.
3. Nothing here justifies re-tagging `v0.1.0`: every item is a patch on top of a released line.

## Open questions
1. Item 4: is `source` a statement about where a component came from, or about which loading path
   brought it in? The answer decides whether the fix is in code or in README.
2. Item 1: is stderr enough, or must `--json` produce a `CommandResult` for a parse error too? The
   second means detecting `--json` before argparse runs.
3. Does the batch end in a `v0.1.1` tag, and who bumps `pyproject.toml`? The project has no release
   procedure yet — the same gap the installation note records.

## Next steps
1. Answer open question 2, then run `fix/cli-json-contract-gaps` (items 1 and 2).
2. Run `fix/function-error-message` (item 5).
3. Answer open question 1, then run `fix/help-component-resolution` (items 3 and 4).
4. Run `chore/repo-hygiene` (items 6, 7, 8).
5. Decide open question 3 and, if the answer is yes, tag `v0.1.1`.

## References
- Branch: `docs/v0_1_0-fix-shortlist`
- Source audits: `2026-08-19-investigation-2_handoff.md` (findings 6-9, 11),
  `2026-08-19-implementation-4_handoff.md` (items 5 and 6 opened there)
- Sessions that closed the rest of that audit: `2026-08-19-implementation-4`,
  `2026-08-19-implementation-5`, `2026-08-19-documentation-5`
- Related architecture note: `2026-08-19-installation-and-distribution.md`
