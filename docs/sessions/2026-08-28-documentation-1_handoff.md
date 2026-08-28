# Session 2026-08-28-documentation-1

## Type
documentation

## Goal
Establish a public-facing motivation document that argues why the project exists, and capture the
architectural ideas raised in the 2026-08-28 external talk as notes.

## Completion criteria
- `docs/motivation.md` exists as a deliberate new slot in the closed document map
  (`docs/rules/documentation-rules.md` §1), indexed in `docs/README.md` and linked from `README.md`.
- The document argues in a fixed challenge/answer structure grounded in the talk, with an explicit
  growth rule, and does not restate `docs/architecture/purpose.md`.
- The two ideas from the talk are captured as architecture notes in the template format.

## Scope boundaries
- No code, no ADR.
- The notes are captured, not triaged: phase assignment stays with an architecture session.
- The ephemeral talk-prep sheet stays outside the repository; only its durable arguments moved in.

## Status
completed

## Result
- `docs/motivation.md` written: the starting point, the one-sentence claim, four challenges with one
  answer each ("agents will do everything", "models are getting better", "isn't this n8n/LangGraph",
  "function versus model"), the applicability section and the boundaries pointer.
- Document map, docs index and `README.md` updated in the same commit as the document.
- Two notes captured: `2026-08-28-authoring-extends-to-components` and
  `2026-08-28-boundary-determinism-function-vs-model`.

## Decisions
- The motivation document is a permanent map slot. Alternatives weighed: extending `purpose.md` was
  rejected because it would load the internal charter, read at every architecture session, with
  external positioning; keeping fragments in `docs/architecture/notes/` was rejected because
  positioning is not an undecided architectural idea.
- Division of labour fixed: `purpose.md` holds the method and boundaries, `motivation.md` holds the
  positioning, the notes hold the design ideas; motivation references their theses without owning
  them.
- Anti-sprawl contract written into the document itself: a fixed set of challenges, a new argument
  merges into an existing answer or replaces one.

## Open questions
None in this session; the open questions of the two captured ideas live inside the notes.

## Next steps
1. On merge into `development`: add the sessions registry row and the two notes registry rows
   (Not triaged).
2. Triage the two notes in a future architecture session.
3. After each future external talk, fold new objections into `docs/motivation.md` under its growth
   rule instead of writing a new prep sheet.

## References
- Branch: `docs/motivation-document`
- ADR: —
- Documents changed: `README.md`, `docs/README.md`, `docs/rules/documentation-rules.md`,
  `docs/motivation.md`, `docs/architecture/notes/2026-08-28-authoring-extends-to-components.md`,
  `docs/architecture/notes/2026-08-28-boundary-determinism-function-vs-model.md`
