# Session note

## Type
documentation

## Goal
State as a rule that a commit message is shown to the user and confirmed before the commit is made.

## Completion criteria
- `docs/rules/general-rules.md` carries the rule, in the form of the rules around it.
- The commit message section of `docs/processes/git-workflow.md` points to it instead of repeating it.
- `CLAUDE.md` carries the rule in its condensed summary, so that the agent sees it in every session.

## Scope boundaries
Only the rule and its two pointers, and this session note. No change to the message form itself, no
git hook, no rule about pushing.

## Status
completed

## Result
`general-rules.md` gained section 12, `Commit confirmation`: the message, subject and body, is
presented and the session waits, and the user confirms it, corrects it or commits themselves. It
covers every commit, including a merge commit and a one line registry commit.

`git-workflow.md` refers to it from the end of its `Commit messages` section. `CLAUDE.md` carries the
same statement as a bullet of its non-negotiable summary, next to the existing rule that code changes
are explained before they are made.

## Decisions
- The rule lives in `general-rules.md` and not in `git-workflow.md`. It binds every session type,
  while `git-workflow.md` describes the form of git artifacts rather than the protocol with the user.
  The considered alternative, placing it next to the message form, keeps the topic together but hides
  the rule from every task that does not route to the git document.
- `.github/copilot-instructions.md` is left untouched: it routes and carries no rule content.

## Open questions
None.

## Next steps
1. Merge `docs/commit-confirmation-rule` into `development` and add the registry row of this session.

## References
- Branch: `docs/commit-confirmation-rule`
- Changed: `docs/rules/general-rules.md`, `docs/processes/git-workflow.md`, `CLAUDE.md`
- Related: `docs/sessions/2026-08-20-documentation-1_handoff.md`, the session that wrote the message
  form this rule refers to.
- No ADR is involved. Nothing was executed: the session changed no code.
