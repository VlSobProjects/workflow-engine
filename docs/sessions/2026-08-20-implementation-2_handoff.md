# Session note

## Type
implementation

## Goal
Implement ADR 016: a `param.`/`output.`/`artifact.` reference resolves inside the text of a field
declared as template text, and the single rendering rule gains the collection case.

## Completion criteria
1. The braced `${...}` form resolves inside every presentation field of `ask`, `$$` writes a literal
   `$`, and a whole-field bare reference keeps working unchanged (§1, §1a).
2. A malformed template fails the node when it is built, reported with the other node configuration
   errors before the run starts; an unresolved reference fails the run at presentation under the
   error class whole-value resolution already raises; neither is routable (§2).
3. `render_value_as_text` renders a list or a dict as compact JSON through the encoder the state
   serialization uses, replacing the Python repr on every text surface (§3).
4. The template-text kind is visible on the ADR 009 help surface, so an author can see which fields
   are templates.
5. `uv run pytest` and `uv run ruff check .` pass, with new tests covering the behaviour and the
   suite checked for guards comparing collection text.
6. `README.md` and `docs/architecture/overview.md` carry the change.

## Scope boundaries
- The template set is `ask` and nothing else: the `llm` prompt joins it when ADR 014 lands.
- No deep resolution into containers (ADR 012 deferred §1) and no declared context map
  (ADR 016 alternative E).
- No pre-processing of the question and no change to the answer path: ADR 015 is Accepted and stays
  as built.
- `examples/` and the ADR-0083 scenario keep their current wording; this branch changes the
  mechanism, not the flows written against it.

## Status
completed

## Result
ADR 016 is implemented. A `param.`/`output.`/`artifact.` reference resolves inside the text of every
presentation field of `ask` through the braced `${...}` form, a malformed template refuses the node
when it is built and an unresolved one fails the run at the question, and `render_value_as_text`
renders a list or a dict as compact JSON. All six completion criteria are met: `uv run ruff check .`
is clean, `uv run ruff format --check .` reports 248 files formatted, and `uv run pytest` reports 416
passed, 28 of them new.

The count the ADR was opened for is answered where it was measured: a question can now carry its
value inside the sentence instead of bending the instruction around a bare `context` field, and a
list reaches the answerer as `["a","b"]` rather than as a Python repr.

## Decisions
1. **The mechanism lives in its own module, `text_interpolation`, not in the action.** `ask` is the
   first template set, not the last: the ADR 014 prompt joins it, and one module holding the syntax,
   the build-time check and the resolution keeps the second caller from copying a third variant of
   the rule. `string.Template` with a never-matching `idpattern` and a dotted `braceidpattern` gives
   the braced-only syntax of §1 with no parser and no dependency.
2. **`braceidpattern` accepts any dotted identifier, not only the three prefixes.** The narrower
   pattern would report `${HOME}` as unreadable syntax; the wider one lets the prefix check name what
   is actually wrong, and both failures are the same configuration error either way.
3. **The collection case falls back to the scalar rule for what `common_encoder` does not carry.**
   The encoder returns `None` for an unknown type and `json.dumps` writes that as `null`, which would
   drop a value from a published question; `render_value_as_text` on the item is the fallback, so a
   `PurePath` inside a list still renders in POSIX form. Recorded in the ADR.
4. **The presentation fields are checked instruction-first.** `description` defaults to the
   instruction string, so checking in field order would report the author's template under a name the
   author never wrote. Recorded in the ADR.
5. **The shipped operator example now interpolates.** The `ask` help example moved its artifact
   reference from a bare `context` field into the instruction, which is the shape the ADR argues for
   and the first thing an author copies.

## Open questions
None from the implementation. One fact is recorded rather than acted on: the ADR-0083 scenario and
the two shipped `ask` templates still phrase their questions in the pre-interpolation shape. They
were left untouched deliberately — this branch changes the mechanism, not the flows written against
it — and re-measuring the scenario against both ADR 015 and ADR 016 is one task, not two.

## Next steps
1. Merge into `development` and set ADR 016 to `Accepted` through the freeze gate; ADR 017 then has
   the single Implementing slot free (rule 11).
2. Re-measure `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` against the
   delivered post function and interpolation together, including whether the flow's questions and the
   two shipped templates should be rewritten to carry their values inside the sentence.
3. ADR 017 as its turn comes; ADR 014 open point 1 is decided for the in-text case and can quote this
   mechanism when it lands.

## References
- Branch: `feature/adr_016-reference-interpolation-in-text`
- ADR: `docs/adr/adr-016-reference-interpolation-in-text.md`
- Added: `src/workflow_engine/text_interpolation.py`, `tests/test_adr016_text_interpolation.py`
- Changed: `src/workflow_engine/actions/action_ask.py`, `tools.py`, `registry/action_registry.py`,
  `help_contract/models.py`, `help_contract/adapters/actions.py`, `help_contract/renderers.py`,
  `tests/test_tools.py`, `tests/test_help_contract.py`, `tests/test_bounded_accumulating_loop.py`,
  `README.md`, `docs/architecture/overview.md`
- Previous session: `2026-08-20-architecture-5_handoff.md`
