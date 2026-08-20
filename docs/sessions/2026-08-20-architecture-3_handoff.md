# Session note

## Type
architecture

## Goal
Decide prompt templating — whether a `param.`/`output.`/`artifact.` reference may resolve inside a
text, and how a non-string value renders once it is inside a sentence — with the count the ADR-0083
investigation produced as the evidence, and open it as an ADR if it is worth deciding.

## Completion criteria
1. The question is argued in critical mode: at least two alternatives, the trade-offs named, the cost
   stated.
2. If it is worth deciding, the ADR exists as `Draft` with its registry row, scoped to what the
   evidence supports; the rendering of a non-string value inside a sentence is part of it, not
   separate.
3. The intersecting open notes are updated per the notes rule: the ADR-0083 coverage note (friction
   1), the ADR 012 deferred questions note (§1), and the engine-as-team-process-carrier note (point
   4) point at the decision instead of standing stale beside it.
4. What the decision unblocks is recorded: reconsidering pre-processing (ADR 015, Leaves open) and
   ADR 014 open point 1.

## Scope boundaries
- No engine code.
- ADR 012 and ADR 013 stay Accepted and unedited.
- ADR 014 is not settled here; only the open point it shares with this decision is named.
- Deep resolution into containers (ADR 012 deferred §1's other branch) is decided only as far as the
  templating decision forces it.

## Status
completed

## Result
ADR 016 "Reference interpolation in text" is open as `Draft` on `development`, registered, with two
small open points. All four completion criteria are met, and the session produced one document beyond
the plan: the discussion of an alternative mechanism separated the form of a published question from
its content, and the form side is captured as a new open note
(`2026-08-20-question-rendering-for-an-audience.md`) instead of being decided on no evidence. The
intersecting notes are updated: the coverage note's step 3 is struck as done, the deferred-questions
note §1 is narrowed, the team-carrier note's point 4 points at ADR 016, and the publishing-boundary
note links to the rendering note that picks up its §1 and §3.

## Decisions
1. **Interpolation, scoped to declared fields.** References resolve inside text as `${...}` (escape
   `$$`) only in fields declared template text — starting with `instruction` and `context` of `ask` —
   never in strings globally, so a literal `${` elsewhere keeps its meaning. The evidence is the
   count of three; the mechanism is the interactive analogue of `function_parameters`: the node
   declares what it needs, the engine resolves it, no user code runs on re-present (ADR 013 §6
   holds).
2. **An unresolved reference is a node error**, not a literal on the published surface.
3. **One rendering rule, extended**: collections render as compact JSON via the state's own encoder
   (a `Path` inside a list renders POSIX), scalars unchanged; this replaces the Python repr on the
   published block independently of templates.
4. **Form is separated from content and not decided here.** The renderer idea — a registered function
   per audience over the published question — is captured in the new note with its fixed points: the
   input is a typed `QuestionBlock` class (the ADR 013 §3 contract made structural, the
   publishing-boundary note's split-the-class option), never `PresentResponse`; the renderer is a
   pure formatter without state; the audience chooses the template, not the node; the rendered form
   is additive to the machine contract.
5. **The full-context processor is rejected in all three shapes** it appeared in during one week —
   pre-function, renderer-with-state, state-in-the-block — with the reasons and the reconsideration
   trigger recorded in the note: re-presenting must not run code, the block is a disclosure boundary,
   a prompt built past the block is not reconstructible from the journal, and the question's content
   must stay readable from the workflow definition. State reaches a question through declaration
   only.

## Open questions
The two open points of ADR 016 (whether `title`/`description` are template fields from the start, and
whether the unresolved-reference error carries its own routable code), plus the open section of the
question-rendering note — none blocks the next step.

## Next steps
1. Take the per-node visit cap to `2026-08-19-hard-node-cap-scoping.md` and decide it there, together
   with the counters question ADR 015's Consequences carry.
2. Open `feature/adr_015-computation-inside-an-interactive-node`, move ADR 015 to Implementing, and
   implement it; ADR 016's two open points can be settled alongside or before its own implementation,
   whichever comes first.
3. When ADR 014 resumes, its open point 1 is decided for the in-text case by ADR 016; the
   question-rendering note ripens into its own ADR once the first two real audiences exist (the CLI's
   human output and one model driver).

## References
- Branch: `development`
- ADR opened: `docs/adr/adr-016-reference-interpolation-in-text.md`
- Note opened: `docs/architecture/notes/2026-08-20-question-rendering-for-an-audience.md`
- Notes updated: `2026-08-19-adr0083-scenarios-coverage.md`, `2026-08-18-adr012-deferred-questions.md`,
  `2026-08-19-engine-as-team-process-carrier.md`, `2026-08-19-interactive-exchange-publishing-boundary.md`
- Evidence: `docs/sessions/2026-08-20-investigation-1_handoff.md`
- Related: ADR 008, ADR 012, ADR 013, ADR 014 (open point 1), ADR 015 (Leaves open)
- Previous session: `2026-08-20-architecture-2_handoff.md`
