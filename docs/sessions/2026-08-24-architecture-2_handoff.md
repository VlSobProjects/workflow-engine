# Session note: 2026-08-24 architecture 2

## Type
`architecture`

## Goal
Execute roadmap step 7: open the output-family ADR from the
`2026-08-24-result-file-composition` note, first deciding under rule 3 whether template text
outside `ask` and document artifacts are one decision or two.

## Completion criteria
- The rule 3 question is answered and the reasoning recorded: one ADR or two, with the split
  named.
- The resulting Draft (or Drafts) is written on `development` with Context, Decision,
  alternatives, `Consumer` naming a scenario that lists it back, and a registry row.
- The `result-file-composition` note is updated (`Affected`/`Status`) so it is not stale next
  to the decision that consumed it.
- The component/ADR boundary is recorded: what is a mere function writable under the current
  architecture and what needs the decision.

## Scope boundaries
- No production code, no tests, no examples.
- ADR 014 and ADR 019 are not edited beyond links their rules require.
- The implementation of the output family is the next session, not this one; moving the ADR to
  Implementing is decided at the end, not assumed.
- The G9 narrowing of ADR 019 stays with roadmap step 11.

## Status
`completed`

## Result
- ADR 020 "Output composition functions" is written as a Draft on `development` with its registry
  row: three functions (grouped-table writer, verbatim text writer, template renderer), the
  template-file loader with build-time check and session snapshot, and the
  substitute-don't-iterate boundary.
- The `result-file-composition` note is `promoted → ADR 020`; its registry row updated.
- `load-test-triage` and `repository-interview` list ADR 020 (lists, registry rows and their
  open decisions 4); the class 4 `folder-inventory-to-csv` lists it at the feature merge, per the
  ADR 014 precedent.
- Roadmap step 7 state records the Draft; the implementation half of the step is next.

## Decisions
1. **Rule 3: one ADR, not two and not a document model.** One decision — output is composed from
   run values through declared, authored surfaces — with three shipped functions as consequences.
   The mechanism-only ADR was rejected for having no consumer able to act on it in phase 2; the
   document model was rejected as unpaid-for width; both are recorded as alternatives in ADR 020.
2. **The family is scenario-derived:** grouped tables (operator report, inventory examples),
   verbatim text write (`repository-interview` od 4, `load-test-triage` od 4, the future `llm`
   output), template render (simple reports, a prompt authored for another model or agent).
   Composed artifact names and the bus-value JSON dump stay in Leaves open with triggers
   (roadmap step 11; the `workflow-authoring` build).
3. **Grouped-table format:** the section table keeps all six syntaxes; the composed file is a
   document for a reader — heading (group value), empty line, table — owner's direction.
4. **Template path:** absolute allowed as-is, relative resolves against the definition file's
   directory — owner's direction; the file is snapshotted into the session at creation so resume
   does not depend on an outside file (ADR 004).
5. **Template text comes only from authored surfaces;** a `${` inside a run value stays literal.
   Templates substitute, never iterate; iteration lives in functions.

## Open questions
None; the function names and signatures beyond the sketches are implementation choices.

## Next steps
1. Roadmap step 7, second half: an `implementation` session moves ADR 020 to Implementing on
   `feature/adr_020-output-composition-functions` — the three functions, the loader with the
   snapshot, e2e coverage, and the examples corrected to the grouped output.
2. Roadmap step 8: ADR 014 into Implementing, after step 7.
3. The `fix/` session for the atomic state write and the session lock, at any pause.

## References
- Branch: `development` — documentation only.
- Documents changed: new `docs/adr/adr-020-output-composition-functions.md`, `docs/adr/README.md`,
  `docs/architecture/notes/2026-08-24-result-file-composition.md`,
  `docs/architecture/notes/README.md`, `docs/architecture/scenarios/load-test-triage.md`,
  `docs/architecture/scenarios/repository-interview.md`,
  `docs/architecture/scenarios/README.md`, `docs/architecture/roadmap.md`, the session registry.
- Related ADRs: ADR 020 (new Draft); ADR 004, 006, 011, 016 (accepted, built on); ADR 014,
  ADR 019 (Drafts, reuse the loader).
- Executes roadmap step 7 (first half), from `2026-08-24-architecture-1` next step 1.
