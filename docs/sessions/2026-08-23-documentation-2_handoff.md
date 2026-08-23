# Session note: 2026-08-23 documentation 2

## Type
`documentation`

## Goal
Write the first class 2 scenario, `repository-interview`: the interview that creates a repository
and its documents, from the owner's account.

## Completion criteria
- `docs/architecture/scenarios/repository-interview.md` exists with all seven header fields of
  `docs/architecture/scenarios/template.md` filled.
- The body records the steps, the data shapes and the open decisions the scenario lacks.
- The scenario registry gains its row when the branch merges into `development`.

## Scope boundaries
- No code, no tests, no examples.
- No ADR is opened, edited or moved; the scenario only names the decisions it lacks.
- The development loop the created repository feeds runs outside the workflow and outside this
  scenario.

## Status
`completed`

## Result
`docs/architecture/scenarios/repository-interview.md` written from the owner's account, with all
seven header fields, six expected paths and six open decisions. Roadmap step 4 marked done, step 5
marked next. The registry rows follow at the merge.

## Decisions
- The scenario's answerer is the agent alone; the human talks only to the agent and never answers
  the engine. The user's technicality is not a routing axis: the same human answers one question as
  a developer and the next as a layman, so the agent absorbs the difference and no guard reads it.
- The prepared data of this class 2 scenario are the intake requirements of the consuming project
  (`java-claude-ai` ADR 0072, 0080, 0083); the dialogue itself is live. The consuming project is
  named by name and ADR number, never by a local path.
- The scenario requires two things of the core beyond what exists: a base write of a string
  parameter into a file (the wider document-artifact family stays in gap G6), and a continuation
  contract so a fresh agent can resume the interview from the semantic context of the run without
  the engine's internal mechanics.
- The consumer's formats, scaffolding and git provisioning stay outside the core as registered
  components of the consuming project (ADR 005); the shipped example ends with what the core alone
  can produce.

## Open questions
None beyond the six open decisions recorded in the scenario, which are input to the resumed
architecture session.

## Next steps
1. Merge into `development`; add the scenario registry row and the session registry row.
2. Resume `2026-08-23-architecture-1` (G1–G12, §3, §4, §6) with this scenario as evidence; its
   decisions revise the roadmap.
3. The scenario's open decisions 1–6 are argued there, the base text write (decision 4) and the
   answerer-visible bounds (decision 1) first.

## References
- Branch: `docs/repository-interview-scenario`
- Source: roadmap step 4; `2026-08-23-architecture-1` §5.2; the owner's account given in session.
- New: `docs/architecture/scenarios/repository-interview.md`.
- Changed: `docs/architecture/roadmap.md` (step 4 done, step 5 next).
- Verification: documentation only; no tests or linter run.
