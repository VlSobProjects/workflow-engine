# ADR process

This document defines the lifecycle of an architecture decision record.

The core principle: an ADR is frozen **after** implementation and testing, not before.
While it is not frozen, it is edited in place. This keeps the number of superseding ADRs low.

## Statuses

### 1. Draft
The decision is being written and discussed. No production code is written for it.
The document is freely editable.

### 2. POC
Optional. Used when the decision cannot be evaluated on paper.
A minimal proof of concept is built to answer a specific open question.
The document stays editable and records what the POC was meant to answer.

### 3. Implementing
The decision is approved for full implementation.
The document stays editable; every meaningful change is recorded in the ADR change log.

### 4. Accepted
Frozen. The document is no longer edited except for editorial fixes, status and links.
The text describes the decision as built, not as originally imagined.

### 5. Superseded
Replaced by another accepted ADR. Applies only to an ADR that was Accepted.

### Rejected
The decision was abandoned before it was frozen.

## Transitions

- Draft to POC: an open question requires evidence from code.
- Draft to Implementing: the decision is clear enough to implement directly.
- POC to Implementing: the open question is answered.
- POC to Draft or Rejected: the POC invalidates the decision.
- Implementing to Accepted: the freeze gate below is satisfied.
- Implementing to Draft or Rejected: the result contradicts the decision itself.
- Accepted to Superseded: a new accepted ADR replaces this decision.

## Freeze gate

An ADR may become Accepted only when all of the following hold:
- the feature branch is merged into `development`,
- the required tests pass, up to and including end to end tests where applicable,
- Context, Decision and Consequences describe the delivered result,
- `docs/architecture/overview.md` describes the delivered architecture, updated in the same merge,
- no POC code reached `development` unless it was raised to production quality.

## Amendment versus reversal

- An amendment refines the decision without contradicting it. It is edited in place while the ADR is not frozen.
- A reversal contradicts the decision itself. It is not an edit: the ADR returns to Draft or becomes Rejected.
- Superseding is reserved for frozen decisions.

## Git linkage

### Where the ADR lives
- A Draft ADR is written directly on `development`, together with its registry row.
- A Draft may stay open indefinitely. Only POC and Implementing are time sensitive.

### Branches
- Entering POC creates `poc/adr_<number>-<short-name>`.
- Entering Implementing creates `feature/adr_<number>-<short-name>`.
- While an ADR is in POC or Implementing, the ADR records its active branch.

### Who edits what
- The ADR body is edited in the active branch and lands together with the code it describes.
- The status field and the registry row are edited only on `development`.

### POC branch
- A POC branch is never merged into `development`.
- When moving to Implementing, the POC branch may be merged into the feature branch, partially reused, or kept untouched as a reference implementation. This choice is free.
- POC code must not reach `development` unless it was raised to production quality.

### Freeze point
- Merging the feature branch into `development` is the point where the freeze gate is checked.
- The status is then set to Accepted on `development`.

Branch naming and merge mechanics are defined in `docs/processes/git-workflow.md`.

## Registry

Every status change is reflected in the ADR registry in `docs/adr/README.md`.
An ADR that stays in POC or Implementing for a long time is visible there and must be resolved rather than left open.
