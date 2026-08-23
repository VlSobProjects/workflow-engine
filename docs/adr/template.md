# ADR template

Copy this structure for every ADR.

## Title
Name the decision.

## Status
One of `Draft`, `POC`, `Implementing`, `Accepted`, `Superseded`, `Rejected`.

## Active branch
The branch where the work is happening while the status is POC or Implementing. Empty otherwise.

## Context
The problem, the constraints and why a decision is needed.

## Consumer
Who acts on the decision — a human, an external program or a model — and the scenario in
`docs/architecture/scenarios/` it serves. Mandatory from Draft on.

## Decision
The decision itself, stated plainly.

## Alternatives considered
Each alternative with its trade-offs and the reason it was not chosen.

## Consequences
What this decision costs, enables and closes off.

## Related ADRs
Dependencies, superseded and superseding ADRs.

## Implementation notes
POC scope, implementation branch and anything the implementation revealed.

## Change log
Meaningful changes while the ADR is not frozen, with the reason for each change.
