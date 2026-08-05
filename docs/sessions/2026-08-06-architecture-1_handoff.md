# Session note

## Type
architecture

## Goal
Open the next architecture decision and write ADR 006 as a draft that states every question the data flow
discussion has to answer.

## Completion criteria
- The next decision is chosen and justified against alternatives.
- ADR 006 exists as a Draft with the open questions, the alternatives and an acceptance scenario.
- The ADR registry and the session registry are updated.

## Scope boundaries
- No decision is taken in this session; the discussion happens in the next one.
- No production code changes.

## Status
completed

## Result
ADR 006 was opened as a Draft. The topic was chosen over "test a complex workflow" because a scenario is
not a decision: the branching folder scan scenario fails today for architectural reasons, and those are
what the ADR has to settle. The draft records the questions, three alternative shapes of the contract and
the acceptance scenario.

## Decisions
- The next ADR is data flow between nodes, not artifacts and not loop semantics; both are narrower and
  depend on it.
- The folder scan scenario becomes the acceptance case of ADR 006 rather than a separate task.
- Global loop budget and retry policy are kept out of ADR 006 and left for a later ADR.

## Open questions
Recorded in ADR 006 as Q1 to Q9. The main ones: who may write parameters, whether
`ActionNodeOutput.parameters` survives as a second channel, whether a node can publish a typed value, how
collections are manipulated, and what an artifact is.

## Next steps
1. Discuss ADR 006 and settle Q1 to Q9, then move it to Implementing.
2. Decide the fate of the unregistered actions found while writing the draft: `FunctionsAction`,
   `PopFromQueue`, `CreateArtifactActionWithContent`.
3. Fix or replace `examples/colect_file_info_workflow.json`, which cannot run today.

## References
- Branch: `development`
- ADR: `docs/adr/adr-006-data-flow-between-nodes.md`
- Registry: `docs/adr/README.md`
