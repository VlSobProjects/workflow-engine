# ADR discussion rules

These rules apply when proposing, discussing or changing an architecture decision.

## 1. Critical mode
Architecture is discussed critically, not agreeably.
State at least two alternatives, name the trade-offs, and state the cost of the change.
Do not accept a proposal only because it was proposed.

## 2. Change the architecture only when it pays
This project already has an architecture. Preserve it by default.
An architectural change is justified only when it is necessary or delivers real benefit.
Record that justification in the ADR.

## 3. One decision per ADR
Keep an ADR focused on a single decision.
Do not bundle unrelated decisions into one document.

## 4. Decision before mechanics
Keep the decision and its rationale separate from implementation detail.
Implementation notes belong in the implementation notes section, not in the decision itself.

## 5. Editing while not frozen
While an ADR is in Draft, POC or Implementing, refine it in place and record meaningful changes in its change log.
Do not create a new ADR to fix a decision that is not yet frozen.
A Draft may not constrain another Draft: a constraint is written only against an accepted ADR.

## 6. Reversal is not an edit
If the result contradicts the decision, return the ADR to Draft or mark it Rejected.
Do not quietly rewrite the decision to match whatever was built.

## 7. POC discipline
A POC exists to answer a specific question and must say which one.
POC code lives in its own branch and is marked as temporary.
Before the ADR is frozen, POC code is either removed or raised to production quality.

## 8. Freezing and superseding
Freeze an ADR only through the freeze gate in `docs/adr/process.md`.
Superseding applies only to frozen decisions.

## 9. Keep the registry truthful
Update the ADR registry in `docs/adr/README.md` on every status change.

## 10. Read the purpose first
Every architecture session starts by reading `docs/architecture/purpose.md`.
Then it reads `docs/architecture/roadmap.md` for the steps of the current phase and its exit scenario.
A decision is argued against the purpose stated there, not against the convenience of the engine.

## 11. Name the consumer
Every ADR names in its `Consumer` section who acts on the decision — a human, an external program or a
model — and the scenario in `docs/architecture/scenarios/` it serves, from Draft on.
The scenario lists the ADR in the same session; the scenario's list is the one truth for the relation.

## 12. Consult the architecture notes
Architecture work reads the open notes in `docs/architecture/notes/`.
A free-scope architecture session ("what architectural work is open?") draws its candidates from them.
When a discussed ADR intersects a note, update the note's `Affected` link or change its `Status`
(`promoted`/`dropped`); do not leave a note stale next to a decision that touched it.
