# Session note

## Type
implementation

## Goal
Make `help-component` answer for the names the engine actually accepts, and make its `source` field
state where a component comes from rather than which loading path brought it in.

## Completion criteria
1. `help-component --component-type codecs --component-name Path` resolves, by the same rule that
   `--input NAME:Path=` and the shipped templates already rely on.
2. An ambiguous bare codec name is reported as ambiguous, not as "not registered".
3. A component registered by a launcher script reports `source: external`, and a component of the
   engine's own package reports `source: core`.
4. `uv run pytest` and `uv run ruff check .` pass, and both behaviours are covered by tests.

## Scope boundaries
- No change to the payload schema of ADR 009: `source` keeps its name, its place and its two values.
- README is not changed: its wording already describes the meaning this session implements.
- Items 6, 7 and 8 of the shortlist belong to their own session.

## Status
completed

## Result
Verified: `uv run pytest` — 271 passed; `uv run ruff check .` — clean; `uv run ruff format --check .`
— 203 files already formatted.

1. `resolve_codec_by_type_name` was split: `find_codec_by_type_name` holds the rule and returns None
   for an unknown name, `resolve_codec_by_type_name` is the raising wrapper the input surface keeps.
   `help-component` now uses the same rule, so `--component-name Path` answers like
   `--component-name pathlib._local.Path`.
2. `source` is derived from the module a component is defined in: the engine's own package is `core`,
   every other module is `external`. `ExternalNames`, `external_names_from_report` and the `external`
   argument of the builder functions existed only to compute the old value and are gone; the help use
   cases now build the engine solely to populate the registries, which `_load_components` says.

## Decisions
1. An ambiguous bare codec name raises rather than reporting a miss, on both surfaces. Several codecs
   answer to it: calling it unknown would be false, and picking one would be a guess. The CLI turns
   the exception into an `error` result with the candidate list, at the same exit code 4 a miss gets.
2. An unknown name stays a miss, so `help-component` keeps its own "is not registered" message and
   stays consistent with the other component types.
3. The adapters mark missing metadata by `source is EXTERNAL`. Under the new rule a component from a
   launcher script without a `summary` now reports the missing-metadata text instead of an empty
   string. That is the intended reading of the field and was accepted, not worked around.
4. README is unchanged. Its wording, "whether it loaded from a core or an external module", is what
   the code now does; it was the code that disagreed with it.

## Open questions
None for these items.

## Next steps
1. Run `chore/repo-hygiene` (shortlist items 6, 7, 8).
2. Close the batch with a maintenance session: bump `pyproject.toml` to `0.1.1`, merge `development`
   into `main` and tag `v0.1.1`.
3. Noted while reading, not fixed and not on the shortlist: `get_codec_by_type_name`
   (`registry/type_registry.py`) has no caller and is now an alias of `CODEC_REGISTRY.get`. It is the
   same class as shortlist item 6 and belongs to that session if it is taken up.

## References
- Branch: `fix/help-component-resolution`
- Source: `2026-08-19-investigation-3_handoff.md` (items 3 and 4)
- ADR 009 (help contract), ADR 012 (codec name resolution)
