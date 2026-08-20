# Session note

## Type
architecture

## Goal
Settle ADR 015 open points 1, 2, 3, 4 and 7 from the evidence of the ADR-0083 investigation, record
the placement and `save_as` findings and the counters cost in the ADR text, then decide whether the
ADR leaves Draft.

## Completion criteria
1. Open points 1, 2, 3 and 4 are settled in the ADR text with the investigation's evidence cited:
   shape, mutability of answered values, write modes, and failure after an accepted answer.
2. The two extra findings are in the text: where the post stage sits in `_start_engine`, and what
   `save_as` comes to mean on a node with a post function.
3. The counters cost — a retry bounded by `max_attempts` leaves no count behind it — is recorded in
   the Consequences.
4. Open point 7 is argued critically and either settled or explicitly kept open with the remaining
   fork stated.
5. The ADR's status decision (stay Draft or move on) is made and the registry reflects it.

## Scope boundaries
- No engine code.
- ADR 013 stays Accepted and unedited; the re-presentation question stays with §6, not here.
- The per-node visit cap is not decided here; it belongs to the hard-node-cap scoping note.
- Prompt templating is not decided here.
- The `APPEND`-may-create question is named, not decided: it is collection-handler semantics outside
  this ADR.

## Status
completed

## Result
All seven open points of ADR 015 are settled and the list is closed — points 5 and 6 as well, beyond
the goal, because the evidence and the arguments were already on the table. The evidence was
spot-checked against the code before use: the placement of the stage, the writes-before-failure-check
order and the `attempt_counters` reset were each confirmed in `engine.py` and `state.py` rather than
taken from the investigation note. The two findings and the counters cost are in the ADR; the
Consequences no longer claim the new injected parameter that the §3 rewrite had already retracted.
The ADR stays Draft and is ready for Implementing; per the process the status changes when the
feature branch opens, so the registry needed no change.

## Decisions
All in ADR 015; the settlements are argued in its text, the changes recorded in its change log.
1. Shape: optional configuration keys on `ask`, no second interactive action (§8) — all four
   questions of the ADR-0083 flow want a function, so a separate action would make the plain form the
   exception an author never picks.
2. A post function may change an answered value (§7): the declaration is a contract about what was
   supplied, and `interactive_answered` means the name was answered, not that the stored value is
   what was supplied.
3. `APPEND` from the function is allowed; the ADR 013 alternative H restriction stays on the answer
   document (§4). Whether `APPEND` may create a collection is collection-handler semantics outside
   the ADR, so the honest node count of the flow is eleven to seven.
4. Failure after an accepted answer is the engine's existing shape, proven by test, and needs no new
   rule (§5).
5. One function, not several: several are imaginable for variant post-processing of a model's answer,
   but one keeps the trivial case trivial and a several-function form is a cheap additive extension
   to make when such a scenario appears.
6. The pre-processing reconsideration is moved out of the blocking list to Leaves open: it waits on
   the templating decision and cannot be settled by this ADR.
7. The standard injection is the whole contract: `Answer` rejected by the evidence, a parallel plain
   mapping rejected on argument (it solves only the read half, reintroduces a retracted injection and
   creates a diverging second representation). Ergonomic access belongs to the output object's API —
   an accessor pair on `ActionNodeOutput` with `APPEND` kept explicit, recorded as an implementation
   note and decided finally at implementation time.
8. Status: Draft until the `feature/adr_015` branch opens, then Implementing. Nothing blocks it:
   no POC is needed and no other ADR is in POC or Implementing.

## Open questions
None new. The questions the investigation surfaced keep their assigned homes: the per-node visit cap
with the hard-node-cap note, the re-presentation wording with ADR 013 §6, the `Path` codec name and
the `dict` key schema with the declaration-shape territory of ADR 012.

## Next steps
1. Decide prompt templating with the count of three bare-value references, which also unblocks
   reconsidering pre-processing; the rendering of a non-string value inside a sentence is part of
   that decision.
2. Take the per-node visit cap to `2026-08-19-hard-node-cap-scoping.md` and decide it there, together
   with the counters question the ADR's Consequences now carry.
3. Open `feature/adr_015-computation-inside-an-interactive-node`, move the ADR to Implementing on
   `development`, and implement: the keys on `ask`, the shared injection runner of §3a, and the
   accessor-pair decision from the implementation notes.
4. Decide separately what a re-presented question tells its answerer (ADR 013 §6 question).

## References
- Branch: `development`
- ADR: `docs/adr/adr-015-computation-inside-an-interactive-node.md` (all open points settled, still
  Draft, ready for Implementing)
- Evidence: `docs/sessions/2026-08-20-investigation-1_handoff.md`, `tests/test_adr0083_scenario.py`
- Previous session: `2026-08-20-investigation-1_handoff.md`
