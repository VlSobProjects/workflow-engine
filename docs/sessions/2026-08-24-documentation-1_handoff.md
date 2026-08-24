# Session note: 2026-08-24 documentation 1

## Type
`documentation`

## Goal
Write the class 2 scenario `workflow-authoring` — a universal authoring cycle in which a workflow
builds any workflow definition node by node, answered by a human or by an agent, validated without
being run — and prepare its registration.

## Completion criteria
- `docs/architecture/scenarios/workflow-authoring.md` exists with the mandatory header of
  `docs/architecture/scenarios/template.md` and a body that states the two answerer variants, the
  expected paths and the open decisions the scenario lacks.
- Each open decision is tied to the gap table of `2026-08-23-architecture-1` §2 where one applies.
- The scenario and session registry rows are written at the merge into `development`, per the
  registries' own rules.

## Scope boundaries
- No code, no tests, no examples, no ADR edits.
- This session is a scenario capture outside the numbered roadmap steps; it is not roadmap step 5
  (the exit-scenario document) and does not reorder the roadmap.
- The decisions the scenario lacks are recorded, not taken.

## Status
`completed`

## Result
`docs/architecture/scenarios/workflow-authoring.md` written: one universal authoring cycle — setup,
then one node per pass with every configuration option reachable, a per-pass choice between adding,
reviewing, validating and finishing — in two named variants of one definition (`human-direct` sets
every parameter, `agent` composes nodes from the client's semantic explanations); seven expected
paths and eight open decisions, each tied to its gap where one applies.

## Decisions
- The scenario is universal — any target workflow — so it fixes no demonstration target and no
  prepared brief; the fixed input data is the engine's own catalog and definition format, the
  intent is live dialogue.
- The run ends with validation through a session initialization that executes nothing — load,
  resolve, build; the first run of the created workflow is its own session outside the scenario,
  because an arbitrary target has no prepared data or answerers the authoring run owns.
- Everything the scenario lacks ships in the core, shaped as universally as the job allows; what is
  scenario-specific is specific to the engine's own definition format, which belongs in the core —
  the opposite placement from `repository-interview`.
- The growth loop is bounded by a declared size cap on the accumulating node list, not by
  `max_visits`, or the cap on the authoring nodes would cap the size of every workflow authored;
  the repair loop is bounded by `max_visits`.
- The component catalog is not recorded as a gap: `help-components` / `help-component` (ADR 007,
  ADR 009) already serve it with examples to both variants; only whether the block should carry a
  catalog slice stays open.

## Open questions
None in the session; the eight open decisions the scenario lacks are recorded in the scenario
document itself.

## Next steps
1. Add the scenario and session registry rows on `development` at the merge.
2. Roadmap step 5 stays next: the class 2 exit-scenario document.
3. The sessions that take the recorded open decisions — G11 authoring surfaces, G5/G6 component
   work, ADR 019 — add this scenario to their evidence when they do.

## References
- Branch: `docs/workflow-authoring-scenario`.
- Documents created: `docs/architecture/scenarios/workflow-authoring.md`, this note.
- Related ADRs: ADR 007, ADR 009, ADR 011, ADR 012, ADR 013, ADR 015, ADR 016, ADR 017, ADR 018;
  Drafts touched by the open decisions: ADR 014 (none), ADR 019.
- Related scenario: `repository-interview` (shared open decisions 2 and 6, opposite component
  placement).
