# Session 2026-08-25-investigation-1

## Type
`investigation`

## Goal
Audit `purpose.md`, `roadmap.md`, `overview.md` and the scenario and notes registries for
contradictions and boundary clarity, and review every `open` note against phase 2 under two
criteria: what phase 2 ships must be functionally finished, and cheap improvements with real
benefit may enter — while the phase must not grow open-endedly and the exit measurement starts
from a frozen code base.

## Completion criteria
- Every contradiction or stale statement found is listed with its document and location.
- Every `open` note has a reviewed verdict for phase 2 — add, keep out, or revisit on named
  evidence — with the reason stated.
- A position on the step order (implementation closed before the exit measurement) is stated
  against the current step list.
- Next steps name the follow-up sessions for whatever the user approves.

## Scope boundaries
- No code changes.
- No edits to `roadmap.md`, the notes, or the scenario documents in this session; fixes are
  proposed, decided by the user, and executed in follow-up sessions.
- No new ADRs and no reopening of frozen ADRs.

## Status
`completed`

## Result
- The three architecture documents (`purpose.md`, `roadmap.md`, `overview.md`) carry no
  contradiction between each other; the drift found is concentrated in documents that reference
  the roadmap's renumbered steps and the state of delivered work:
  1. `docs/architecture/scenarios/load-test-triage.md` — "the hand-build of this scenario
     (roadmap step 12)" is stale: after `2026-08-25-documentation-2` the hand-build is step 15.
  2. Same document, section "Open decisions the scenario lacks": items 1–4 describe ADR 014 as
     Draft, the `llm` node as missing, the dictionary functions and the answer-keys guard as
     absent and ADR 020 as pending — all delivered. The exit scenario is the hand-build author's
     task statement, so it must be brought current before step 15.
  3. `docs/architecture/notes/README.md`, Current-phase row of the two-drifts note: "(roadmap
     steps 11–12)" is stale; the drift-B protocol now lives in steps 13–15.
  4. `2026-08-25-two-drifts-and-their-measurement.md`: "Nothing in the roadmap accounts for it
     today" (data generation) is stale — step 14 now carries it.
  5. `2026-08-18-recovery-and-resilience-roadmap.md`: its "Roadmap" section still assigns (a)
     manual takeover and (b) retry/backoff to phase 2, contradicting its own triage into "Later
     phases"; and it calls (b) "unblocked" by ADR 014 without noting that ADR 014 froze "no
     retry policy", so (b) is now a supersession, not an addition.
  6. `2026-08-19-interactive-exchange-publishing-boundary.md` §1: the unused
     `PresentResponse` symbols it lists were removed by the step 11 refactor; the section reads
     as if they remain.
- Two boundary-clarity gaps, both one-sentence fixes:
  1. Phase 2 exit says "an author deliberately working from the operator documentation alone"
     but, unlike phase 3, names no evidence mechanism for that restraint; state what records it
     (the session note of the hand-build) or soften the claim.
  2. `purpose.md` says the authoring proof is "assisted authoring, where the engine asks,
     validates and assembles", while the phase 3 exit row says only "through the published
     surfaces alone"; nothing states that the agents author *via* the `workflow-authoring`
     flow, and the purpose wording reads as an engine feature when it is a workflow the engine
     runs.
- Notes review verdict: no note moves into phase 2. Retry/backoff and the ADR 012 §4 input
  transport hazard are the two real candidates; both are deferred pending evidence from step 13
  (live rehearsal) and the step 15 hand-build, because each requires superseding a frozen ADR
  and the gate path does not need them. The hard-node-cap and codec questions wait on exactly
  the numbers and surfaces later phases produce. The only work added to the phase is
  documentation actualization (the stale items above), which is a precondition of a clean
  starting point, not an extension.
- Step-order position: steps 1–12 are done, so "implementation closed before scenario work"
  already holds structurally. The clean-baseline requirement binds step 15 and the number
  declaration inside step 14, not step 13 — the rehearsal exists to surface changes and its
  findings land before 14. E2e scenario measurement starts only after any step 13 fallout is
  closed.

## Decisions
None — investigation only; all fixes proposed for user decision.

## Open questions
- Whether the phase 2 exit-row wording gains its evidence sentence or is softened.
- Whether the phase 3 exit row states that the agents author via the `workflow-authoring` flow.

## Next steps
1. A `docs/` session to actualize `load-test-triage.md` (step reference and the open-decisions
   section), the two-drifts registry row and note line, the recovery note's phase-2 paragraph,
   and the publishing-boundary §1 state — before steps 13–14 begin.
2. The same or a follow-up session applies the two one-sentence boundary clarifications if
   approved.
3. Proceed to roadmap step 13; re-evaluate retry/backoff and the input-transport fix on its
   findings.

## References
- Branch: `development`
- Documents audited: `docs/architecture/purpose.md`, `docs/architecture/roadmap.md`,
  `docs/architecture/overview.md`, `docs/architecture/scenarios/load-test-triage.md`,
  `docs/architecture/scenarios/README.md`, `docs/architecture/notes/README.md` and all thirteen
  `open` notes.
- Related ADRs: ADR 012, ADR 014, ADR 019, ADR 020, ADR 021 (referenced, none changed).
