# Session 2026-08-25-documentation-4

## Type
`documentation`

## Goal
Actualize the documents the `2026-08-25-investigation-1` audit found stale — the exit-scenario
document, the notes registry and three notes — and apply the two approved boundary
clarifications to `purpose.md` and `roadmap.md`.

## Completion criteria
- `load-test-triage.md` names roadmap step 15 for the hand-build and its open-decisions section
  states what is actually still open after ADR 014/020/021 and roadmap step 10.
- The two-drifts registry row and note body name the steps that now carry the drift-B protocol
  and the data generation.
- The recovery note's roadmap section no longer assigns work to phase 2 and states that
  retry/backoff now supersedes ADR 014's no-retry clause.
- The publishing-boundary note §1 records that the unused `PresentResponse` symbols are gone.
- `roadmap.md` states the evidence mechanism for the phase 2 hand-build claim and that the
  phase 3 agents author through the `workflow-authoring` flow.
- `purpose.md` attributes the assisted-authoring behaviour to a workflow the engine runs, not to
  the engine.

## Scope boundaries
- Factual actualization and the two approved sentences only; no step is added to or removed from
  the roadmap, no note changes its `Status` or its phase, no ADR text is touched.
- No code changes.

## Status
`completed`

## Result
- `docs/architecture/scenarios/load-test-triage.md`: the hand-build reference corrected to
  roadmap step 15; the open-decisions section rewritten — the delivered work (ADR 014, the G5
  dictionary family, the G4 answer-keys guard, ADR 020) summarized as closed with the step 10
  readings carried in, and the five genuinely open decisions kept: the handover composition
  measure, the G7 default failure route, the prompt location, the G11 lower bound, the data.
- `docs/architecture/notes/README.md`: the two-drifts row now names roadmap steps 13–15.
- `docs/architecture/notes/2026-08-25-two-drifts-and-their-measurement.md`: the data-generation
  bullet records that roadmap step 14 now carries it.
- `docs/architecture/notes/2026-08-18-recovery-and-resilience-roadmap.md`: the roadmap section
  retitled to the note's later-phase triage, (b) marked as a supersession of ADR 014's no-retry
  clause with step 13 named as the evidence point, and the `Affected` header corrected to match.
- `docs/architecture/notes/2026-08-19-interactive-exchange-publishing-boundary.md` §1: one line
  records that the step 11 refactor removed the unused symbols.
- `docs/architecture/roadmap.md`: a phase 2 evidence sentence added beside the phase 3 paragraph,
  and the phase 3 paragraph states the agents author through the `workflow-authoring` flow.
- `docs/architecture/purpose.md`: "the engine asks, validates and assembles" is now "a workflow
  the engine runs asks, validates and assembles".

## Decisions
None beyond executing what `2026-08-25-investigation-1` proposed and the user approved.

## Open questions
- The recovery note has now been amended for the third time; by the notes lifecycle rule its next
  touch should close or split it. Raised to the user, deliberately not executed here.

## Next steps
1. Merge into `development` and add this session's registry row.
2. Proceed to roadmap step 13, the live-model rehearsal.

## References
- Branch: `docs/post-audit-actualization`
- Preceded by: `2026-08-25-investigation-1_handoff.md`
- Documents changed: `docs/architecture/purpose.md`, `docs/architecture/roadmap.md`,
  `docs/architecture/scenarios/load-test-triage.md`, `docs/architecture/notes/README.md` and the
  three notes named above.
