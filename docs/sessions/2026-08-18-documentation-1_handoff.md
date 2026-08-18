# 2026-08-18 documentation 1 — architecture notes channel

## Type
documentation

## Goal
Introduce a sanctioned, low-friction channel for durable architectural ideas that outlive a session and
precede an ADR, and audit the commit-to-`development` policy to cover its registry.

## Completion criteria
- `docs/architecture/notes/` exists with a `README.md` (purpose, boundary, structure, lifecycle, naming,
  commit policy, consumption ritual, registry) and a `template.md` (fixed header + free body).
- `documentation-rules.md` amended so the channel is allowed: the map includes it, and §6/§7 (which
  named `notes` as forbidden and kept working notes out of the repo) carve out this one governed channel
  while still forbidding ad hoc reports/summaries/plans/work logs.
- `git-workflow.md` allows direct-to-`development` commits of notes and requires every touched registry
  (ADR, sessions, notes) to be updated on merge.
- `adr-rules.md` obliges architecture work to consult and reconcile notes.
- Routing added in `docs/README.md`, `AGENTS.md`, `CLAUDE.md`.
- The recovery/resilience roadmap discussion captured as the first note.

## Scope boundaries
- No code, no tests, no ruff (documentation only).
- The channel is one new governed type; the ban on ad hoc side documents is unchanged.
- No ADR is opened here; the recovery roadmap stays a note until a phase-2 architecture session promotes it.

## Status
completed

## Result
Created the `docs/architecture/notes/` channel (README + template) with a fixed header
(`Date`/`Trigger`/`Status`/`Affected`) and a free body, a three-state lifecycle
(`open`/`promoted`/`dropped`, terminal notes retained), date-based naming, and a registry. Amended
`documentation-rules.md` §1/§6/§7, `git-workflow.md` (direct-commit allowance + update-all-registries on
merge), and `adr-rules.md` (new rule 10: consult and reconcile notes). Added routing in `docs/README.md`,
`AGENTS.md`, `CLAUDE.md`. Captured two first notes: the recovery/resilience roadmap, and the deferred
architectural questions from the ADR 012 implementation (facts linked to the ADR change log, questions
only).

## Decisions
- The notes channel is a deliberate amendment to the documentation principle that kept working notes out
  of the repo (`documentation-rules.md` §7); it is the single sanctioned in-repo channel for
  architectural thinking, not a reopening of ad hoc side documents.
- Fixed header + free body: uniformity where it matters (indexing, lifecycle), freedom where the value is
  (the idea itself).
- Notes are consumed during architecture work (adr-rules §10), which is what makes capture worthwhile.

## Open questions
None.

## Next steps
1. Merge `docs/architecture-notes-channel` into `development`; on merge add this session's sessions-registry
   row and reconcile the notes registry row.
2. In the next architecture session, review the recovery/resilience note before choosing phase-2 work.

## References
- Branch: `docs/architecture-notes-channel`
- New: `docs/architecture/notes/README.md`, `template.md`, `2026-08-18-recovery-and-resilience-roadmap.md`,
  `2026-08-18-adr012-deferred-questions.md`
- Changed: `docs/rules/documentation-rules.md`, `docs/processes/git-workflow.md`,
  `docs/rules/adr-rules.md`, `docs/README.md`, `AGENTS.md`, `CLAUDE.md`
