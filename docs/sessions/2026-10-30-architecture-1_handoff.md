# Session 2026-10-30-architecture-1

## Type
`architecture`

## Goal
Land the desk letter EX-21 (2026-10-06, one question on what a capture carries, and one change to
its description): decide whether the triage needs the rig's label-to-band attribution, write the
decision into the `load-test-triage` scenario and answer the rig.

## Completion criteria
- The question is decided with its alternatives and the cost stated.
- The input data of `docs/architecture/scenarios/load-test-triage.md` states what the decision
  makes the capture carry and what it never takes as input.
- An answer to EX-21 stands on the desk as a draft; only the user releases it.
- `What it changed` of EX-21 is filled once the branch is merged.

## Scope boundaries
- No domain parsing module and no parsing shape: the injector half still waits for the first real
  result log.
- No change to the variant map, the flow shape or the drift-B protocol of the scenario.
- No change to the rig's files or its description format beyond what the answer asks of it.

## Status
`completed`

## Result
The scenario's input data now says that the load profile carries the service levels — a 95th
percentile per band of operations and a hard ceiling over all — together with the rig's published
rule mapping a sample's label to its band, that the domain module attributes every sample itself,
and that the rig's own percentiles and verdict are never input. The answer to EX-21 is written on
the desk as a draft.

## Decisions
1. **The capture should carry the label-to-band rule (alternative A).** Without it the per-band
   service levels in the description cannot be applied by any reader outside the rig, and only the
   hard ceiling remains usable; a breached level is the most direct symptom the clean path and the
   decision read. The rule is configuration, not a result, so the two readings of a run stay
   independent, which the drift-B measurement depends on as much as the rig does. Rejected:
   B, declining the attribution because the verdict names a cause rather than a service-level
   compliance — it leaves the per-band levels dead data and reopens the question the first time a
   level is needed; C, deferring to the injector half of the domain module — the question has been
   open on the rig's side since 2026-08-31, and a rule published before the capture campaign costs
   less than one added after it. Cost: one field in the rig's description, one sentence in the
   scenario, and a parser that reads the rule when the injector half is written.
2. **The rounding change lands as nothing.** Since the rig's commit `b35fa0d` (2026-10-05) the target
   rates and the table's growth in the load profile are written to three decimals, half up; earlier
   captures keep the unrounded figures, names and types unchanged. No parser exists yet to be
   affected; the fact is kept here for the injector half of the domain module, which must accept
   both forms.

## Open questions
- The exact form in which the rig publishes the rule — a table of labels, a prefix convention or a
  pattern — is the rig's to choose; the parser follows it.

## Next steps
1. The user releases the draft answer to EX-21 on the desk.
2. Merge `docs/ex-21-capture-band-attribution` into `development` and add the registry row.
3. Fill `What it changed` of EX-21 with the scenario and the commit.
4. When the injector half of the domain module is written: read the band rule from the load
   profile and accept both rounded and unrounded figures.

## References
- Branch: `docs/ex-21-capture-band-attribution`
- Desk letter: EX-21 (2026-10-06, one question on what a capture carries, and one change to its
  description)
- Changed: `docs/architecture/scenarios/load-test-triage.md`
- Earlier decisions on the rig's data: `2026-08-26-architecture-1`, `2026-08-28-architecture-1`
