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
