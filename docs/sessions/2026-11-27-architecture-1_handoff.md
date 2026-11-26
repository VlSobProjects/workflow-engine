# Session 2026-11-27-architecture-1

## Type
architecture

## Goal
Decide which step of phase 2 comes next after step 17 — the authoring skill of step 18, the
documentation digest with a model, the notes triage, or a return to step 14 — and record the order in
the roadmap.

## Completion criteria
- `roadmap.md` carries the decided order in its phase 2 step table, with this session named among the
  sessions that revised it.
- This note records the alternatives weighed, their trade-offs and their cost, and why the chosen one
  was taken.
- The two notes opened on 2026-11-25 have a phase assigned, to be reflected in the notes registry when
  the branch merges.

## Scope boundaries
- The open questions of the `documentation-digest-showcase` note are not settled here.
- The four other untriaged notes are not triaged here.
- No ADR is opened, no code, no workflow file.

## Status
`completed`

## Result
- `roadmap.md`: step 19, the documentation digest with a model, added next after step 17; step 18
  marked as moved to phase 3; the phase 3 paragraph lists the floor measurement as its first known
  work; this session named among the revisions of the phase 2 order.
- The `documentation-digest-showcase` note records the decided roadmap place and drops it from its
  open questions.
- Triage of the two notes of 2026-11-25 decided (Decision 4); the registry rows move at the merge.

## Decisions
1. **The documentation digest with a model is the next step, step 19, ahead of step 14.**
   Alternatives weighed:
   - *Step 18, the authoring skill now* — shows assembly by an agent and gives phase 3 its floor;
     costs the decision on the place of a Skill, a format owned by a third party, plus one or two
     sessions; serves nothing of the phase 2 exit, must not be used by the hand-build of step 15,
     and a floor measured now would be taken on documentation that steps 14 and 15 still change.
   - *The digest* — shows what `purpose.md` promises and the step 17 demonstration leaves out: a model
     call with its audited facts, a context bound, a refusal handled as a value, on a task a reader
     recognises; it runs the `llm` stack against a live model again, which serves steps 14 and 15;
     the core stays untouched (the owner's option B); costs one architecture session on the note's
     open questions, two or three implementation sessions and a maintenance session for CI; delays
     the phase exit further and brings a model host reachable from the internet and a CI secret.
   - *The notes triage alone* — cheap, prepares the phase close, moves neither the showcase nor the
     phase.
   - *Step 14* — the main line to the phase exit, the most expensive, reverses the showcase priority
     set by `2026-11-21-architecture-2`.
2. **Step 18 moves to phase 3 as the floor measured at its start**, on the documentation phase 2
   leaves, so the floor and the phase 3 exit are measured against the same documentation and the
   hand-build of step 15 keeps its evidence. The place of a Skill in the documentation map stays
   with the architecture session that opens it.
3. **Step 19 keeps the order of ADR 022's step**: an architecture session settles the digest note's
   open questions first — among them whether the external module and its dependencies need an ADR.
4. **Triage**: `documentation-digest-showcase` goes to the current phase (it is step 19);
   `report-home-in-journal-details` goes to later phases — the demonstrations run in CI, whose home
   directory names no one, so the leak concerns an operator who publishes a report, a release
   concern, and its fix beyond a statement would supersede the accepted ADR 022.

## Open questions
- The open questions of the `documentation-digest-showcase` note.
- The four untriaged notes left: `authoring-extends-to-components`,
  `boundary-determinism-function-vs-model`, `published-contract-and-consumer-requests`,
  `storage-read-contract`.

## Next steps
1. At the merge into `development`: the sessions registry row; in the notes registry, move
   `documentation-digest-showcase` to "Current phase" and `report-home-in-journal-details` to "Later
   phases".
2. The architecture session of step 19: the open questions of the digest note, and whether the
   external module needs an ADR.
3. The implementation sessions of step 19, then the maintenance session adding the run to the
   `Demonstration` workflow.
4. A triage session for the four notes left, before the phase is closed.

## References
- Branch: `docs/next-showcase-step`
- Changed: `docs/architecture/roadmap.md`,
  `docs/architecture/notes/2026-11-25-documentation-digest-showcase.md`
- Related: ADR 014, ADR 020, ADR 022; notes `2026-11-25-documentation-digest-showcase`,
  `2026-11-25-report-home-in-journal-details`, `2026-11-21-run-report-and-public-showcase`,
  `2026-08-21-agent-instruction-and-skill`; session `2026-11-21-architecture-2`
