# Session note

## Type
documentation

## Goal
Give `docs/processes/git-workflow.md` a commit message template, so that the form the repository
already follows is written down instead of being inferred from `git log`.

## Completion criteria
- `docs/processes/git-workflow.md` carries a `Commit messages` section that states the subject form,
  the body form, the `Verified:` line and the merge commit form.
- The template describes the practice visible in the recent history, not an invented convention.
- No other rule document repeats the same statement.

## Scope boundaries
Only the new section in `git-workflow.md` and this session note. No history rewriting, no commit
hook, no change to the branch categories, and no change to any other rule document.

## Status
completed

## Result
`docs/processes/git-workflow.md` has a `Commit messages` section between `Working rules` and
`Merging`. It states the subject form `<type>: <one line>` with the branch category as the type, the
80 character subject limit, the prose body wrapped at 100 characters, the `Verified:` line required
of every commit that touches code, and the case where a subject alone is the whole message. The
merge commit form `Merge <branch>: <what the branch delivers>` is stated as a bullet of `Merging`,
next to the other merge rules.

The template was derived from the last eighty commits, not invented: the type set, the `Verified:`
wording, the body style and the merge subject form all already occur in the history.

## Decisions
- The commit type is the branch category in its commit form, so `feature/` commits as `feat:`. One
  vocabulary, two spellings, instead of a second closed list to keep in sync.
- `Verified:` is mandatory for a commit that touches code and absent from one that does not. The
  general rule already demands that tests and the linter run before a task is reported done; the line
  makes the claim part of the permanent record rather than of the conversation.
- The `Co-Authored-By` trailer is deliberately not documented. It is added by the tool that produced
  the commit, and the section describes what the author writes.
- The subject limit is 80 characters, which matches the practice and is not the 120 of `ruff`.
- The `git commit -F <file>` habit moved into this section as its source of truth; `CLAUDE.md` keeps
  it as part of its condensed summary.

## Open questions
None.

## Next steps
1. Merge `docs/commit-message-template` into `development` and add the registry row of this session.

## References
- Branch: `docs/commit-message-template`
- Changed: `docs/processes/git-workflow.md`
- No ADR is involved. Nothing was executed: the session changed no code, and the repository has no
  documentation linter.
