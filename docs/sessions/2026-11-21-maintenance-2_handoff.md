# Session 2026-11-21-maintenance-2

## Type
`maintenance`

## Goal
Run the tests in CI only where they pay off, while the secrets scan keeps running on every push.

## Completion criteria
- gitleaks moves to its own workflow file that runs on every push and every pull request, unfiltered.
- `ci.yml` runs ruff and pytest on a push to `development` or `main`, on a pull request, and on a
  manual `workflow_dispatch`; a push or pull request that changes documentation only does not run it.
- Documentation only means `docs/**`, `README.md`, `AGENTS.md`, `CLAUDE.md` and `LICENSE`;
  `examples/` is read by the tests and is not documentation.
- Both workflow files pass `actionlint`.
- The installation and distribution note no longer states that the tests run on every push.
- How the triggers were checked is recorded as it actually happened.

## Scope boundaries
- No change to the jobs themselves: the same steps, versions and matrix.
- No branch protection, no required status checks.
- No answer to which platforms the project claims to support.

## Status
`in progress`

## Result
- `.github/workflows/secrets.yml` added: the gitleaks job moved out of `ci.yml` unchanged, run on
  every push and every pull request without a path filter.
- `.github/workflows/ci.yml` now runs on a push to `development` or `main`, on a pull request and on
  `workflow_dispatch`; push and pull request ignore `docs/**`, `README.md`, `AGENTS.md`, `CLAUDE.md`
  and `LICENSE`. The job, its steps, versions and matrix are unchanged.
- The installation and distribution note, item 2, states the new triggers.
- How the triggers were checked:

  | Check | How | Result |
  | --- | --- | --- |
  | Workflow files | `actionlint` 1.7.7 in a container, run by the owner, `-verbose` | both files linted, 0 errors |

## Decisions
1. **Tests run after the merge, on a pull request, or on demand; not on every push of a branch.** A
   push of an unfinished branch spent the three-system matrix, the slow macOS queue included, on
   work not yet meant to pass. Running on every branch was rejected for that cost; a commit-message
   marker was rejected because the built-in `[skip ci]` also skips the secrets scan and a custom one
   reads only the head commit. The price is that a failure on Linux or macOS is learnt after the
   merge, unless the branch is run by hand before it; Windows stays covered by the local `pytest`
   the verification rule requires.
2. **ruff runs with the tests, not on every branch push.** It is run locally before every commit.
3. **The secrets scan has its own workflow file.** A path filter applies to a whole workflow, and
   the scan must run on every change, documentation included.
4. **Documentation only is a closed list of paths, not `**.md`.** `examples/` holds walkthroughs in
   Markdown beside the templates the tests read, so a pattern on the extension would skip runs that
   matter.
5. **The path list is written twice, not as a YAML anchor.** It is not established that the
   `actionlint` version in use accepts anchors; five repeated lines are cheaper than the doubt.

## Open questions
- If branch protection with required status checks is turned on later, a documentation-only change
  leaves the `ci.yml` checks pending, because the workflow never starts. That needs a decision then,
  not now.

## Next steps
1. Push the branch: only the `Secrets` workflow is expected to run.
2. Merge into `development` and push: `CI` is expected to run on all three systems.
3. Run `gh workflow run ci.yml --ref <branch>` on the next task branch to confirm the manual run.

## References
- Branch: `chore/ci-trigger-policy`
- Session: `2026-11-21-maintenance-1` (next step 3)
