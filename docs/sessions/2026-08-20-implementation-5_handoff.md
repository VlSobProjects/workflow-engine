# Session note

## Type
implementation

## Goal
Put the surfacing and the accumulating post function into the core, as component work under the
delivered ADR 015, and fold the four data-only nodes of the ADR-0083 scenario onto the questions they
serve, confirming or refuting the eleven-to-seven prediction of the coverage note.

## Completion criteria
1. Two registered functions ship in the core, both taking the injected `output`: one surfacing a
   declared answer value into the output text, one appending the answer to a collection parameter and
   reporting whether the loop has enough. Both are covered by unit tests and by an end-to-end run
   through the CLI.
2. `CHECK_ROOT`, `CHECK_ISSUES`, `FQ_CHECK` and `FQ_COLLECT` are gone from
   `tests/test_adr0083_scenario.py`, folded into `ASK_ROOT`, `ASK_INSPECT` and `ASK_FOLLOWUP`, and the
   flow still covers every ADR-0083 node type it covered before.
3. The resulting node count is recorded against the prediction of eleven-to-seven.
4. `README.md` and `docs/architecture/overview.md` carry what the change made inaccurate, and item 4
   and item 5 of "What is still missing" in
   `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` stop being a prediction.
5. `uv run pytest` and `uv run ruff check .` are run from the command line and reported.

## Scope boundaries
- No engine change: the ADR 015 stage exists and is not touched, and no ADR text is reopened.
- No new guard and no new action. The fold uses the two functions this session adds plus the
  components already registered.
- The CLI read surfaces discussed alongside this session — narrowing `show-state`, the parameter and
  journal commands — are captured in `docs/architecture/notes/2026-08-20-interview-continuation-context.md`
  and belong to their own ADR, not here.
- Frictions 2 (in-graph budget checkpoint) and 3 (script-running function for `S`) stay untouched.

## Status
completed

## Result
`echo_answer` and `collect_answer` ship in the core, in the new module
`src/workflow_engine/actions/answer_functions.py` registered as a core module. The ADR-0083 scenario
is folded from eleven nodes to seven: `CHECK_ROOT` and `CHECK_ISSUES` became `echo_answer` on the
questions they stood behind, and `FQ_CHECK` and `FQ_COLLECT` became one `collect_answer` on the
question they surrounded. The flow covers every ADR-0083 node type it covered before, and the
prediction of the coverage note is confirmed as measured rather than argued.

Verification: `uv run pytest` — 441 passed; `uv run ruff check .` — all checks passed;
`uv run ruff format --check .` — 257 files already formatted.

## Decisions
1. **The pair is `echo_answer` and `collect_answer`, in a module of its own.** `echo_answer` pairs by
   name with `echo_value`: one surfaces a value from the state, the other a value from an answer that
   has not reached the state. They live together in `actions/answer_functions` rather than beside
   `echo_value` and `append_to_param`, because what they have in common is the injected answer, not
   what they do with it.
2. **A refusal keeps the answered writes.** Both functions fail the node by editing the output they
   were given, not by returning a fresh one, so an answer that was accepted still lands on the bus
   when the function cannot compute. This differs from the other core functions, which build a fresh
   error output — they have no accepted answer to preserve. The engine already applies a node's writes
   before it looks at the failure, so this makes the pair agree with it rather than being the one
   exception.
3. **A node that computes cannot also route on the answer text**, because the function's result is the
   whole output (ADR 015 §4). `ASK_ROOT` used to read the word "abort" out of a success answer; the
   walk-away is now the declared failure answer the contract always had (`review_abandoned` in the
   node's error catalogue), which is what the coverage note's row `A` maps `auto_log_stop` to anyway.
   The same consequence moves `save_as`: at `ASK_INSPECT` it now keeps the surfaced issue list, not
   the answer text.
4. **`max_visits` left `ASK_ROOT`.** With the check inside the question, the correction re-asks in
   place, which is an attempt, so `max_attempts: 2` bounds it at the question. Nothing in the folded
   flow leaves a node and comes back, which is the only thing the cap is for, and a declared cap that
   nothing can reach is misleading configuration. The scenario therefore stops exercising ADR 017,
   which keeps its coverage in `tests/test_adr017_max_visits.py`.
5. **`CHECK_ISSUES` folded as an equality, not as a count.** `is_collection_size_at_least` resolves its
   collection from the state, where an answered value has not landed, so the size of an answered
   collection is not checkable inside the node that asked. The branch is an `equals` on the rendered
   value — an empty issue list is literally `[]` (ADR 016). The alternative, a guard reading the
   pending writes of the output, was deliberately not built: it is a third component with a contract
   of its own, and one flow is not evidence for it.

## Open questions
1. Whether a guard should be able to read a value the current output is about to write — the
   component that would let the node that asked route on the *size* of an answered collection rather
   than on its rendering. Deferred until a second flow asks for it; recorded in item 5 of "What
   ADR 015, 016 and 017 changed" in the coverage note.

## Next steps
1. ADR and implementation for the session read surfaces: `show-state` narrowed to the state of the
   run, parameters split into a listing command and a value-by-name command, the journal given its own
   bounded surface. Captured in
   `docs/architecture/notes/2026-08-20-interview-continuation-context.md`; removing `parameters` from
   `show-state` is a removal, which is why it needs the ADR.
2. ADR 014 as its turn comes, quoting the `text_interpolation` module for its open point 1.
3. Friction 3, the script-running function for `S`, as an external module.

## References
- Branch: `feature/adr_015-post-function-components`
- Added: `src/workflow_engine/actions/answer_functions.py`, `tests/test_answer_functions.py`
- Changed: `src/workflow_engine/bootstrap/plugin_manifest.py`, `tests/test_adr0083_scenario.py`,
  `README.md`, `docs/architecture/overview.md`,
  `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`
- Component work under: ADR 015 (Accepted and delivered; its text is untouched)
- Previous session: `2026-08-20-architecture-6_handoff.md`
