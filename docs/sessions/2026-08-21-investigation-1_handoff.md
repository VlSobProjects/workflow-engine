# Session note

## Type
investigation

## Goal
Capture, as architecture notes, the first use case the project was built for — an agent taking a
technical-support call to the point where a human operator can act on it — and measure it against the
components the engine actually has.

## Completion criteria
1. A note holds the use case itself: what the flow does, node by node, and what it needs that is not
   there. Every gap is stated as a measured fact against a named file, not as an impression.
2. The same note records the proposal that this use case becomes a required exit condition of phase 2,
   and the finding that no document in the repository holds the phase plan that such a condition would
   belong to.
3. A second note holds the other half: how an agent that is told nothing about the scenario drives the
   engine at all, why that instruction is a new kind of document the map does not admit, and what it
   measures about the published question block.
4. Both notes carry the `open` status, and their registry rows are added on `development` when
   the branch merges, per the commit policy of `docs/architecture/notes/README.md`.
5. This session note is completed and committed.

## Scope boundaries
- No code, no test and no template is written or changed. The gaps are recorded, not closed.
- `tests/test_adr0083_scenario.py` is not touched, in this session or by the sessions these notes
  propose: it is the yardstick for an external repository's scenarios and stands on its own.
- No ADR is opened. The notes name candidates for decisions; deciding them is later work.
- The document map is not changed here. The note states that admitting the agent instruction requires
  a deliberate map decision, and leaves that decision to the session that writes it.
- The phase plan document the second criterion finds missing is not created here.

## Status
completed

## Result
All five criteria met, with two notes instead of one: the use case and the way an agent drives any
workflow are different tensions, and the sessions that pick them up will not be the same session.

`2026-08-21-support-intake-use-case.md` holds the support-intake flow node by node and measures it
against the component inventory. Five findings, each against a named file: a dictionary parameter can
be created by nothing; a composed artifact name is inexpressible because `template=True` exists in one
file only; the single output shape is a table in six syntaxes; no guard can check that an answered
dictionary carries the declared items; and the one step that already works is the helpful stop that
produces no deliverable. It also carries the exit-condition proposal and the finding that no document
holds the phase plan.

`2026-08-21-agent-instruction-and-skill.md` holds the other half: the scenario-free instruction as a
measurement of whether the published question block is self-sufficient, five questions it will have to
answer, the three places it could live and why none of them is free, and the first record of the Skill
intention anywhere in the repository.

Nothing was verified by running anything: no code, test or template was touched, so there was nothing
to run.

## Decisions
1. **Two notes, not one.** The use case asks what the engine must be able to express; the instruction
   asks how an agent uses the engine at all. Splitting them keeps each note pickable by one session.
2. **The recorded next step of `2026-08-21-documentation-1` is deliberately not followed.** That note
   planned to lift the workflow out of `tests/test_adr0083_scenario.py` into `examples/` and have the
   test load the shipped file. The opposite is now the position: the test is a measurement against an
   external repository's decision record and must stand still, while a shipped template is a product
   that will change as the missing components arrive. Merging them would freeze the product to serve
   the measurement. The duplication of a seven-node interview shape between the two is accepted for
   that reason, and is recorded here so that a later session does not deduplicate it as tidying.
3. **ADR-0083 stays out of anything user-facing.** It belongs to the external `java-claude-ai`
   repository; the reference is anchored here only by `2026-08-19-adr0083-scenarios-coverage.md` and
   the ADRs that cite it. A walkthrough in `examples/` has no such anchor, so its reader would be sent
   to a decision record that does not exist in this project.
4. **The exit-condition proposal is recorded as a proposal.** A note is, by its own README, not a
   decision, and there is no other document that could hold a phase boundary. Making it binding is a
   separate decision that depends on the open question below.
5. **Nothing about the missing components is decided.** The output family, the composed artifact name,
   the dictionary parameter and the checklist guard are named as candidates and left open.

## Open questions
1. Does the phase plan get a document of its own, and if so, what map row admits it? Until it has one,
   a phase boundary can only live inside a frozen ADR or inside a note that is explicitly not a
   decision.
2. Are the three missing output shapes one decision about what a run may hand out, or three separate
   components? The leading position is one ADR over the family.
3. Where does the agent instruction live, and is it one document or two?

## Next steps
1. Merge this branch into `development` and add the two note rows to
   `docs/architecture/notes/README.md` and the session row to `docs/sessions/README.md`.
2. Ship the reduced form of this scenario as the fourth template — an `implementation` session on
   `feature/interview-to-table-example`. It is the part of the support intake that the engine can
   express today: seven nodes, a `ticket_id` input, the account number checked by `is_output_number`
   on the node that asked for it, a diagnosis answered as a list, up to two accumulated follow-up
   pairs, a handover gate that fails the run under its own code when the intake is not fit to hand
   over, and one CSV deliverable. The walkthrough, its row in `examples/README.md` and its row in the
   root `README.md` table go with it, and the claim in `examples/README.md` that every template
   declares its inputs is re-checked against it. What the full scenario additionally needs is already
   measured in the use-case note, so that session does not re-derive it.
3. Write the agent instruction as a `documentation` session, after step 2, so it can be exercised
   against two interactive templates rather than reasoned about. It carries the map decision that
   admits it.
4. Decide the output family under an ADR. This is what the use case is actually blocked on, and it
   precedes any attempt at the full flow.
5. Clean the component inventory in its own `refactor/` session, after step 4 — never folded into
   work that adds components.

## References
- Branch: `docs/support-intake-scenario-note`
- Added: `docs/architecture/notes/2026-08-21-support-intake-use-case.md`,
  `docs/architecture/notes/2026-08-21-agent-instruction-and-skill.md`, this note
- Previous session: `2026-08-21-documentation-1_handoff.md`
