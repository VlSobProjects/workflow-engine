# Session note: 2026-08-21 investigation 2

## Type
`investigation`

## Goal
Read the engine's interactive surfaces from the answerer's seat — by driving the synthetic ADR-0083
coverage scenario by hand, one question at a time — and record what they do and do not publish.

## Completion criteria
- The scenario is driven far enough by hand to see a prepared question, an instruction node, the
  collecting loop and a branch decision, plus at least one refusal path and one rejected answer.
- Every finding is either captured in a new architecture note or added to an existing one; nothing
  stays only in the conversation.
- The note and session registries carry their rows.
- No file of the project outside `docs/` is touched.

## Scope boundaries
- No code, no tests, no examples, no fixes. Findings are recorded, not acted on.
- The run itself happened in a runtime root outside the repository; nothing from it is committed.
- The synthetic scenario is treated as coverage of the node types, not as a use case: its wording is
  not evaluated as a design.
- No ADR is opened. The findings name their alternatives and stop there.

## Status
`completed`

## Result
Two new notes and two amended ones.

- `2026-08-21-answer-document-and-its-audience.md` (new). The published question block states what to
  answer and never how: the answer envelope of ADR 013 §4 is documented in `README.md` and the
  overview but is absent from the block, while the block does publish `generic_error_code` — half the
  return contract crosses the publishing boundary and half does not. An answerer holding only the
  paused result cannot compose a valid answer. Second finding: `node_id` is published to a reader who
  cannot use it, because `resume` addresses a session and not a node. Also checked and recorded: the
  audience-adaptation idea covers the outbound direction only; the answer form is fixed in the core,
  is not configurable, and its adaptation is unrecorded rather than decided.
- `2026-08-21-command-result-cost-for-a-machine-reader.md` (new). One paused result carries the
  instruction three times, the status three times, the node id and the session id twice each, the
  session-constant fields on every turn, and its empty fields always; `data.timestamp` is the state's
  creation time and does not move between turns. The contract question underneath: neither ADR 007
  nor ADR 013 states who the payload is addressed to, so nothing can be dropped from it today.
- `2026-08-21-agent-instruction-and-skill.md` (amended). Three of its predicted gaps were measured.
  Its "already in place" line about the answer document was wrong in the way that matters and moved
  to the gaps; gap 2 generalizes from attempts to every bound the author sets — a collecting loop's
  `minimum` included — under one statement: every bound in this engine is invisible to the party it
  binds.
- `2026-08-20-question-rendering-for-an-audience.md` (amended). The return direction is named as
  absent from it and pointed at the new note, with the reason the two are not mirror images. Recorded
  too: the single renderer in the tree formats the internal `PresentResponse` and is reached only by
  a test's `print`, which is the shape that note's own first fixed point rules out.

## Decisions
None. An investigation records findings; every option named in the two new notes stays open.

## Open questions
1. Does the answer envelope belong in the published block, in a machine-readable help payload fetched
   once, or in the agent instruction — and if the last, the agent-instruction note has to say that
   the block is not self-sufficient by design.
2. Should the answer form be adaptable per audience at all, given that a parser decides what reaches
   the state while a formatter only decides how a sentence reads.
3. Who is the command result addressed to, and what may be omitted from it.
4. Whether a bound the author sets — attempts, visits, a collecting loop's minimum — should be
   visible to the answerer, and what publishing it would cost.

## Next steps
Taken in a later session, in the user's order of priority. Nothing here blocks anything.

## References
- Branch: none. Committed directly to `development`: documentation only, no code, no branch.
- Verification: none run, and none applicable — no code, test, example or configuration was touched.
- Related ADRs: ADR 007, ADR 009, ADR 013, ADR 018.
- Documents changed: the four notes above and the two registries.
