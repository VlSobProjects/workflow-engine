# Session note

## Type
architecture

## Goal
Settle the two open points ADR 016 carries — which fields of `ask` are template text, and what class
an unresolved reference raises — so the decision can leave Draft with nothing left to discover at
implementation time.

## Completion criteria
1. Open point 1 is answered against the code, with the alternatives named, and §1 states the decided
   field set.
2. Open point 2 is answered, and §2 states both the error class and why the failure is not routable.
3. Whatever the settlement of those two surfaces as undecided is decided in the same text rather than
   left for the implementation to invent; the open-points list ends empty.
4. The ADR change log records the settlement; the registry row stays truthful; the architecture notes
   that point at ADR 016 are checked against the result.
5. No engine code, and the status stays `Draft`.

## Scope boundaries
- No engine code and no tests: this session decides, it does not build.
- ADR 016 stays `Draft`. Moving it to `Implementing` and creating its branch opens the implementation
  session, as it did for ADR 015.
- Alternative E (the declared context map) and ADR 012 deferred §1 (deep container resolution) stay
  open; this session does not narrow them further than the Draft already did.
- ADR 014 and ADR 017 are not edited; the ADR-0083 coverage note keeps its pending re-measurement.

## Status
completed

## Result
ADR 016 has no open points left and is ready for `Implementing`. Both points it carried were decided
against the code rather than on paper, and settling them uncovered a third question the Draft had not
asked — what a lone `$` means once a field is declared a template — which is decided in the same
text. The decision section grew a subsection (§1a, the field set) and §2 was rewritten from one
failure into two; alternatives G and H record the two shapes rejected on the way. All five completion
criteria are met.

## Decisions
All in ADR 016, with a change log entry there.
1. **The template set is every presentation field of `ask`** — `title`, `description`, `instruction`,
   `goal`, `context` and the five list fields, each list templated per element (§1a). Two properties
   of the code decided it against the narrower set the evidence alone would scope (alternative G):
   all ten already resolve whole-value references through one function, so a narrower set would be a
   rule with nothing behind it; and `description` defaults to the `instruction` string, so the
   commonest shape — a templated instruction with no description — would otherwise publish an
   unrendered `${param.x}` as the description and as the result message of the paused run.
2. **Only the braced form is a reference.** `$param.root` is a malformed template, not a second
   spelling: one syntax is read faster in review, and the unbraced form has no end — `$param.root.`
   would swallow the full stop of its own sentence.
3. **Two failures, at two times, neither routable** (§2). A malformed template is a configuration
   error of the node, raised at build time and aggregated per node before the run (ADR 001); an
   unresolved reference stays the existing resolution error class and fails the run at presentation.
   Neither is routable for the same reason ADR 017 gave for its entry check: the presentation is
   built before the node has an output, so no guard has anything to read. The consequence is stated
   rather than hidden — a broken `artifact.` reference inside a question is less routable than the
   same reference in an automatic node, where `artifact_not_found` becomes an error value.
4. **Lenient substitution rejected** (alternative H): the leniency that would keep `$5` intact also
   keeps `${param.rooot}`, which is exactly what §2 exists to stop reaching the answerer. The cost is
   an escape rule, and the break it imposes — existing `$` in one of the ten fields must become `$$`
   or the node stops building — is recorded in the Consequences. No workflow in this repository
   carries such a `$`.

## Open questions
None new, and none left in ADR 016. The questions it names as deliberately left open are unchanged:
the declared context map (alternative E), deep container resolution (ADR 012 deferred §1), and
widening the rendering rule to the remaining scalars.

## Next steps
1. Move ADR 016 to `Implementing` on `development`, open
   `feature/adr_016-reference-interpolation-in-text`, and implement it. Rule 11 allows it: the single
   slot is free. The implementation checks the suite for guards comparing collection text, which
   change from a Python repr to compact JSON.
2. ADR 017 follows; it has no open points either.
3. Beyond them: ADR 014 resumes with its open point 1 decided for the in-text case; the ADR-0083
   coverage note still owes its re-measurement against the delivered ADR 015 stage; the
   re-presentation wording question (ADR 013 §6) still wants its own decision.

## References
- Branch: `development`
- ADR: `docs/adr/adr-016-reference-interpolation-in-text.md`
- Updated: `docs/adr/README.md` (summary and `Depends on`, which gains ADR 001)
- Checked and left unchanged: the four architecture notes pointing at ADR 016
  (`2026-08-18-adr012-deferred-questions.md`, `2026-08-19-adr0083-scenarios-coverage.md`,
  `2026-08-19-engine-as-team-process-carrier.md`, `2026-08-20-question-rendering-for-an-audience.md`)
  — each describes ADR 016 at a level the settlement does not contradict, so rule 10 needed no edit.
- Grounded in: `src/workflow_engine/actions/action_ask.py` (the ten presentation fields and the
  `description` default), `src/workflow_engine/actions/base_actions.py` and
  `src/workflow_engine/engine.py` (presentation is outside the error-value conversion),
  `src/workflow_engine/exceptions.py`, `src/workflow_engine/workflow.py`
- Verification: none run, and none applicable — no code changed in this session.
- Related: ADR 001, ADR 009, ADR 013, ADR 014, ADR 015, ADR 017
- Previous session: `2026-08-20-implementation-1_handoff.md`
