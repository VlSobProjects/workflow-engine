# Session note: 2026-08-23 documentation 1

## Type
`documentation`

## Goal
Carry out the four decisions of `2026-08-23-architecture-1` §5: the consumer rule, scenarios as a
kind of document, the roadmap, and the registries rewritten to one-sentence rows and split by phase.

## Completion criteria
- `docs/adr/template.md` has a mandatory `Consumer` section; the freeze gate in `docs/adr/process.md`
  requires evidence from a scenario that the consumer can act; `docs/rules/adr-rules.md` forbids a
  Draft constraining a Draft (§5) and reads the roadmap after the purpose (§10).
- `docs/architecture/scenarios/` exists with a README, a template and an empty registry, and the
  document map admits it.
- `docs/architecture/roadmap.md` exists with the steps of phase 2 and its exit scenario, and the
  document map admits it.
- The session registry holds only the current phase, with an `ADR` column and one-sentence rows; the
  phase 1 rows live in `docs/sessions/phase-1.md` in the same form; no session file is moved.
- The notes registry is split into current phase, later phases, not triaged and closed, with
  one-sentence rows; no note file is moved.
- The three entrypoints route to the roadmap and the scenarios.

## Scope boundaries
- No code, no tests, no examples.
- No scenario is written; the first class 2 scenario is the next session.
- No note is triaged: every `open` note is listed as not triaged until the architecture session
  assigns its phase.
- No ADR text changes; the `Consumer` section applies to ADRs written or edited from now on.

## Status
`completed`

## Result
All completion criteria met. `Consumer` is in the ADR template and rule 11 of the ADR rules; the freeze
gate asks for scenario evidence; rule 5 forbids a Draft constraining a Draft; rule 10 reads the roadmap.
`docs/architecture/scenarios/` has its README, template and empty registry; `docs/architecture/roadmap.md`
carries the phases and the phase 2 steps of `2026-08-23-architecture-1` §6 as proposed. The 66 phase 1
session rows are in `docs/sessions/phase-1.md`, the registry holds the current phase, both with an `ADR`
column and one-sentence rows; the notes registry has its four sections with one-sentence rows. The
entrypoints, `docs/README.md` and the merge rule of the git workflow route to the new documents.

## Decisions
- The phase archive is a file beside the registry (`docs/sessions/phase-1.md`), not a directory: a
  directory would move files or hold one file. Finding a session by ADR is served by the `ADR` column,
  not by the location.
- Scenarios have a `template.md` like the notes, so the fixed header is copied, not retyped.
- The roadmap records the order of `2026-08-23-architecture-1` §6 as proposed, marked as such; the
  architecture session that decides §6 rewrites it.
- Every `open` note is listed as not triaged; the triage belongs to the architecture session.
- Phase 1 closed at the merge of `development` into `main` after the `v0.1.0` tag (2026-08-19), not at
  the commit that brought `purpose.md` into `development` as `2026-08-23-architecture-1` §5.3 put it:
  the 32 sessions from the opening of ADR 013 on are phase 2. The architecture session records the
  correction when it resumes.

## Open questions
None.

## Next steps
1. Merge, add the registry row.
2. The session that writes the first class 2 scenario (the interview that creates a repository and its
   documents).
3. Resume `2026-08-23-architecture-1`: G1–G12, §3, §4, §6; rewrite `roadmap.md` with its decisions.

## References
- Branch: `docs/documentation-system`
- Source of the decisions: `2026-08-23-architecture-1_handoff.md` §5.
- Changed: `docs/rules/adr-rules.md`, `docs/adr/process.md`, `docs/adr/template.md`,
  `docs/rules/documentation-rules.md`, `docs/architecture/notes/README.md`, `docs/sessions/README.md`,
  `docs/processes/git-workflow.md`, `docs/README.md`, `AGENTS.md`, `CLAUDE.md`,
  `.github/copilot-instructions.md`.
- New: `docs/architecture/roadmap.md`, `docs/architecture/scenarios/README.md`,
  `docs/architecture/scenarios/template.md`, `docs/sessions/phase-1.md`.
- Verification: documentation only; no tests or linter run.
