# Session note: 2026-08-24 documentation 2

## Type
`documentation`

## Goal
Write the class 2 exit-scenario document of phase 2 (roadmap step 5), so that the `Consumer`
section of ADR 014 names an existing scenario.

## Completion criteria
- `docs/architecture/scenarios/load-test-triage.md` exists with the mandatory header of
  `template.md` and describes the fetch → aggregate → decide → branch → hand over run of the
  phase 2 exit scenario: fully automatic, on prepared data, with a local model per step.
- The scenario records as open decisions the measurements the roadmap assigned to it:
  G4 (answer keys), G5 (dict assembly, splitter, domain fetch as an external module),
  G6 (the handover document), G7 (failure-route verbosity) and G11 (the authoring surface),
  per `2026-08-23-architecture-1` §2.
- The scenario registry row, the session registry row and the roadmap step 5 state are ready to
  be added on `development` at the merge.

## Scope boundaries
- No ADR is edited; the ADR 014 and ADR 019 edits are roadmap step 6.
- No code, no tests, no examples; the components the scenario lacks are named, not built.
- The `support-intake` reformatting stays in roadmap step 9.

## Status
`completed`

## Result
- `docs/architecture/scenarios/load-test-triage.md` written: the phase 2 exit scenario as a
  class 2 document, eight expected paths, seven open decisions carrying the G4–G7 and G11
  measurements and the `prompt_ref` question ADR 014 deferred.

## Decisions
- The scenario is fully automatic: no `ask` node; the human appears only as the recipient of the
  handover. A confirmation `ask` at the verdict was considered and rejected to keep the exit
  scenario a pure run of the second archetype of ADR 014 §1.
- The prepared data describes a fictional order-processing service in neutral formats (JSON, CSV,
  plain log lines), not the report format of a named load-testing tool, so the scenario binds the
  engine to no external tool; the publication gate replaces the prepared data with a live system.
- The identifier is `load-test-triage`; the domain fetch and parse functions ship as an external
  module beside the scenario, per the G5 decision, while only generic bus work goes to the core.

## Open questions
None. The open decisions the scenario itself lacks are recorded inside the document.

## Next steps
1. At the merge into `development`: add the scenario registry row, the session registry row, and
   flip roadmap step 5 to done.
2. Roadmap step 6: an `architecture` session edits ADR 014 to the narrow Draft with `Consumer`
   naming `load-test-triage`, and decouples ADR 019 with the shared-mechanism guards.
3. Roadmap step 8: build this scenario by hand on prepared data and measure open decisions 2–7.

## References
- Branch: `docs/load-test-triage-scenario`
- Documents changed: `docs/architecture/scenarios/load-test-triage.md` (new), this note.
- Related ADRs: ADR 014 (Draft, the consumer link this session prepares), ADR 005, ADR 006,
  ADR 011, ADR 012, ADR 016, ADR 017, ADR 018.
