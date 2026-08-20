# Session note

## Type
implementation

## Goal
Rewrite the shipped `ask` flows in the shape ADR 016 made possible: every prior value a question shows
its answerer stands inside the sentence instead of beside it as a bare presentation field.

## Completion criteria
1. The three `context: param.x` fields of `tests/test_adr0083_scenario.py` (`ASK_INSPECT`,
   `ASK_FOLLOWUP`, `ASK_APPROVE`) are gone and their values stand inside the instruction.
2. `examples/approve-and-copy.json` carries the file and its size inside the instruction; its
   `context` and `hints` fields are gone.
3. Every assertion that read a moved value out of `question["context"]` reads it out of the
   instruction instead, in both `tests/test_adr0083_scenario.py` and
   `tests/test_adr013_e2e_interactive.py`.
4. `README.md` shows the example's published question as it is now published.
5. The comments in the scenario that state a value can only be shown as a field of its own are
   rewritten, so the flow no longer teaches the pre-ADR-016 shape.
6. The coverage note records that the interpolation half of its item 4 is done and that the
   node-folding half is not.
7. `uv run ruff check .` and `uv run pytest` both run and both pass.

## Scope boundaries
- The node-folding half is not done: no node is removed, no post function is added, and the node
  count of the scenario stays eleven. It waits on the note's open question 1, which is an
  architecture session.
- No engine change. ADR 016 is delivered; this session only uses it.
- The `hints` field is not re-purposed: the example drops it rather than filling it with new text.
- No new ADR and no change to an accepted one.

## Status
completed

## Result
The four presentation fields that carried a prior value beside its sentence are gone, and the values
stand inside the instruction each question publishes.

`tests/test_adr0083_scenario.py`: `ASK_INSPECT` names the folder, `ASK_FOLLOWUP` carries the issue
list, `ASK_APPROVE` carries the report paragraph. `examples/approve-and-copy.json`: `ASK_APPROVAL`
names the file and the size the previous node measured, dropping both `context` and `hints`. Every
assertion that read one of those values out of `question["context"]` reads it out of the instruction,
and two of them also assert that the field is no longer published at all, so a value moved cannot
silently become a value duplicated. One assertion is new: the follow-up question is checked for the
compact JSON of the issue list, which is the half of ADR 016 that nothing outside
`tests/test_adr016_text_interpolation.py` exercised in a real flow.

`README.md` shows the example's question block as it is now published. The comments in the scenario
that taught the pre-ADR-016 shape are replaced by one that states the JSON rendering.

The coverage note records the split: the interpolation half of its item 4 is delivered, the
node-folding half is not and stays a prediction with the node count of eleven unchanged. The notes
registry row carries the same state.

Verification: `uv run ruff check .` clean, `uv run ruff format --check .` clean (252 files),
`uv run pytest` 424 passed.

## Decisions
1. **`hints` was moved, not kept.** `hints: ["param.source_size"]` in the example is the same shape
   as a `context` field — a prior value shown beside the sentence because it could not go inside it —
   so it moved with the rest and the field was dropped rather than refilled with new text. The field
   itself stays covered by `tests/test_adr016_text_interpolation.py`, which templates all five list
   fields.
2. **The example's question does not name `target_dir`.** The pre-ADR-016 question showed only the
   source file, and interpolation is not a licence to tell the answerer more than it was told before.
   Making the question complete is a separate judgement about the example, not part of moving a value.
3. **No node was folded and no post function was written.** The fold needs a function taking the
   injected `output`, and no core function takes one — re-confirmed in this session across
   `base_functions.py` and `modify_param_functions.py`. Registering one inside the scenario test the
   way ADR 015's tests do would have confirmed the prediction at the price of a yardstick that no
   longer runs on the shipped core alone, which is the property the scenario exists to demonstrate.

## Open questions
None new. The note's open question 1 — whether a surfacing and an accumulating post function belong in
the core — is unchanged and now blocks the only remaining half of the rewrite.

## Next steps
1. Decide the note's open question 1 as an architecture session: the surfacing and accumulating post
   functions in the core, or proven in an external module first. Everything the fold needs waits on it.
2. Fold the four data-only nodes once that decision exists, in its implementation session. It also
   rewrites the ADR 017 case in the scenario: with the check inside `ASK_ROOT`, the retry becomes an
   attempt and `max_attempts` becomes the bound there.
3. ADR 014 as its turn comes, quoting the `text_interpolation` module for its open point 1.
4. Friction 3, the script-running function for `S`.

## References
- Branch: `refactor/adr_016-values-inside-the-sentence`
- Changed: `examples/approve-and-copy.json`, `tests/test_adr0083_scenario.py`,
  `tests/test_adr013_e2e_interactive.py`, `README.md`,
  `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`,
  `docs/architecture/notes/README.md`
- Uses: ADR 016 (text interpolation)
- Previous session: `2026-08-20-investigation-2_handoff.md`
