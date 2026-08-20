# Session note

## Type
investigation

## Goal
Re-measure `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` against ADR 015, ADR 016
and ADR 017 together, now that all three are Accepted and delivered, and answer the note's own open
next step: whether the flow's questions and the shipped `ask` template should be rewritten to carry
their values inside the sentence.

## Completion criteria
1. Every row of the mapping table is checked against the delivered engine, and the rows the three ADRs
   changed are rewritten: `Q`, `A`, `FQ` and `attempt_counters` / `max_visits`.
2. The four items of "What building it found" are re-stated: what each of the three decisions
   answered, and what is left of the item.
3. Friction 1 is closed and recorded as closed, with the frictions that remain kept.
4. The header (`Affected`, `Status`) and the notes registry row carry the new state.
5. The rewrite question is answered with a verdict and a reason, and the work it implies is registered
   as a next session rather than done here.
6. Every claim about the engine is either verified in the code in this session or marked as a
   prediction the rewrite would have to confirm.

## Scope boundaries
- No code change: the scenario flow, the shipped examples and the engine are untouched. This session
  measures; the rewrite it recommends is its own session.
- No new ADR and no change to an accepted one.
- Frictions 2 (in-graph budget checkpoint) and 3 (the script-running function for `S`) are not
  re-opened; they are unaffected by the three decisions.

## Status
completed

## Result
The note is re-measured. All eleven rows of the mapping table were checked against the delivered
engine; five were rewritten (`Q`, `A`, `FQ`, `attempt_counters` / `max_visits`, logging). Three of the
four "What building it found" items are answered and the fourth is softened, each annotated in place
with a pointer to the new section that explains it. Friction 1 is struck through and marked closed by
ADR 016, keeping the measurement that produced it. The header, the intro verdict and the notes
registry row carry the new state; the note stays `open`.

The substance of the re-measurement: the engine's one core gap is gone. A question carries its value
inside its own sentence, the node that asks checks what it bound before its transitions run, and a
node bounds its own re-entry. What is left of the ADR-0083 mapping is two frictions that belong to
decisions still open — the in-graph budget checkpoint and the script-running function — plus two items
this session added, both about the distance between a delivered mechanism and a usable flow.

Verification: reading only. No code, no test and no example was changed, so neither pytest nor ruff
was run — `git status` is clean apart from the three documents this session writes.

## Decisions
1. **The rewrite question is answered "yes, and in two parts of different cost."** The interpolation
   half is free: the mechanism is core, so the scenario's three `context: param.x` fields and the one
   in `examples/approve-and-copy.json` move inside the sentence with nothing else changing, and the
   shipped example is the first thing an author copies. The node-folding half is not free — see
   decision 2 — so the two halves are recorded as one next session that may deliver the first half
   alone.
2. **No core registered function takes the injected `output`.** Checked across every core function
   module: ADR 015 shipped the mechanism and the two functions that prove it live in
   `tests/test_adr015_post_function.py`. `echo_value`, the obvious candidate, cannot serve — it reads
   its value from the state, where an answer has not landed, and returns a fresh output that would drop
   the answered writes. So the fold the mechanism makes possible costs an external module today. The
   note records the question of whether that pair belongs in the core and deliberately does not answer
   it: that is an architecture session, not a measurement.
3. **The node count stays a prediction, marked as one.** Four of the scenario's eleven nodes look
   foldable into the post function of the question they serve, leaving seven, and folding the check
   into `ASK_ROOT` would turn its retry from a fresh visit into an attempt — making `max_attempts` the
   bound there and `max_visits` no longer the thing that saves the run. None of it was built, and this
   note's own standard is measured evidence, so it is written as the prediction the rewrite has to
   confirm rather than as a result.
4. **The `pathlib._local.Path` observation is left standing.** ADR 016 decided how a *value* renders
   inside text, not how a codec names itself in the answer declaration, so the published name is
   unchanged. Recorded next to the observation so the next reader does not re-check it.

## Open questions
1. Whether a surfacing and an accumulating post function belong in the core. Small, general and used
   by every interactive loop, which argues for the core; the first components whose contract is the
   injected answer, which argues for proving them in an external module first. Recorded in the note as
   item 5 of "What is still missing".
2. What a re-presented question tells its answerer. ADR 013 §6 is untouched: an author can now write
   the reason into a parameter that the question interpolates, but a plain `resume` still returns the
   identical block with an empty `errors` map. The engine has no rule; only the author has a way.

## Next steps
1. Rewrite the flows against the three decisions, as an implementation session: the scenario's three
   `context` fields and the shipped `examples/approve-and-copy.json` question move inside the sentence.
   Whether the same session folds the four data-adjusting nodes depends on open question 1, because the
   fold needs functions that do not exist yet.
2. ADR 014 as its turn comes; its open point 1 is decided for the in-text case by ADR 016, and it can
   quote the `text_interpolation` module rather than re-decide the syntax.
3. Friction 3, the script-running function for `S`, is the last item of the note's own order and the
   one that finishes the first goal of phase 2.

## References
- Branch: `docs/adr0083-coverage-remeasure`
- Changed: `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`,
  `docs/architecture/notes/README.md`
- Re-measured against: ADR 015, ADR 016, ADR 017
- Previous session: `2026-08-20-implementation-3_handoff.md`
