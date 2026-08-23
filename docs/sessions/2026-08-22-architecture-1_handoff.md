# Session note: 2026-08-22 architecture 1

## Type
`architecture`

## Goal
Decide who the published question is addressed to and what it carries, and capture the decision as a
Draft ADR that supersedes the part of ADR 013 which left the audience undeclared.

## Completion criteria
- A Draft ADR exists with the decision, at least two alternatives per contested point, the cost of
  the change, and the list of ADRs it supersedes, amends or constrains.
- The ADR registry carries its row.
- Every open architecture note the decision settles is marked `promoted` with the ADR named; every
  note it touches without settling carries the ADR in its `Affected` line.
- The session registry carries this session.
- No file outside `docs/` is touched.

## Scope boundaries
- No code, no tests, no examples: the ADR stays Draft and enters no POC in this session.
- The guard that routes on a node's counters is named as a dependency and not decided here.
- The form of the future LLM node's prompt is constrained, not designed: ADR 014 stays Draft and is
  not edited.

## Status
`completed`

## Result
ADR 019 "The question document and its renderers", Draft, written on `development` with its
registry row. It records the diagnosis the discussion reached: ADR 013 §1 (one answer contract,
whoever answers) holds; ADR 013 §6 and alternative G (the engine declares no audience, so it
publishes the internal presentation whole) were a decision and a wrong one, not an omission, and are
superseded. The decision: the interactive action publishes a typed question document addressed to
the party that answers, rendered by a registered renderer chosen by the caller, the node or the
workflow in that order; the answer protocol stays single and is published inside the document with
the value form each codec declares; the bounds the author sets become `node.` references in template
text; a dedicated command publishes the document and the session commands keep the telemetry.

Notes settled by the ADR and marked `promoted → ADR 019`:
`2026-08-20-question-rendering-for-an-audience.md`,
`2026-08-21-answer-document-and-its-audience.md`,
`2026-08-21-command-result-cost-for-a-machine-reader.md`. Note touched and re-linked:
`2026-08-21-agent-instruction-and-skill.md` (its gap 2, the invisible bounds, is what the `node.`
references answer; the instruction itself is not decided here).

## Decisions
All in ADR 019. The ones that cost the most discussion:
- `node.` is a closed vocabulary of runtime counters; a `state.` prefix was considered and rejected
  because it would make the state model a contract an author writes against.
- The `instruction-only` mode carries the author's own prompt from a file beside the workflow,
  interpolated by ADR 016; the engine appends the protocol and nothing of the presentation.
- A guard over the node's counters is a separate decision: today the only exit from a re-ask loop is
  `max_attempts_exceeded`, and an author cannot route "after N attempts, escalate".

## Open questions
1. Whether an external codec that declares no value form is refused at registration or published as a
   string with a warning.
2. Whether the audit copy of a rendered document is a session file or a journal event.
3. Whether the selection of the renderer at call time may be forbidden by the author; the draft says
   it may not.

## Next steps
1. Open the ADR for the counter guard (the exit from a re-ask loop by routing), as the dependency
   ADR 019 names; it may stay Draft until ADR 019 enters Implementing.
2. Move ADR 019 to Implementing on `feature/adr_019-question-document` once the three open questions
   are settled; no POC is foreseen, because every mechanism it uses exists.
3. Re-read ADR 014 against ADR 019 §3 before ADR 014 enters Implementing: the LLM node consumes the
   question document, not its own prompt assembly.

## References
- Branch: none. Written directly on `development`, as `docs/adr/process.md` prescribes for a Draft
  ADR and its registry row; documentation only, no code.
- Verification: none run, and none applicable — no code, test, example or configuration was touched.
- Related ADRs: ADR 019 (new), ADR 013 (superseded in part), ADR 007, ADR 005, ADR 016 (amended when
  ADR 019 is accepted), ADR 014 (constrained), ADR 017.
- Documents changed: the new ADR, the ADR registry, the four notes and their registry rows, the
  session registry.
