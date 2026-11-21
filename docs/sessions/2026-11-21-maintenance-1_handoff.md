# Session 2026-11-21-maintenance-1

## Type
`maintenance`

## Goal
Add a GitHub Actions pipeline that runs ruff, pytest and gitleaks on every push and pull request.

## Completion criteria
- `.github/workflows/ci.yml` triggers on every push and every pull request, with read-only
  permissions.
- One job installs the locked environment with `uv sync --locked` and runs `ruff check`,
  `ruff format --check` and `pytest` on ubuntu, windows and macos.
- One job scans the full git history with a pinned gitleaks binary whose checksum is verified.
- Every action and tool is pinned to an exact version.
- The workflow file passes `actionlint`.
- The architecture note on installation and distribution no longer states that there is no CI.
- How each platform was checked is recorded as it actually happened.

## Scope boundaries
- No decision on which platforms the project claims to support: that stays open question 2 of the
  installation and distribution note.
- No README badge, no Dependabot, no branch protection, no release pipeline.
- No CI metadata quality gates from ADR 009.

## Status
`completed`

## Result
- `.github/workflows/ci.yml` added with two jobs, `checks` on a three-OS matrix with
  `fail-fast: false`, and `secrets` on ubuntu. A newer push to the same ref cancels the older run.
- Pinned versions: `actions/checkout` v7.0.1, `astral-sh/setup-uv` v10.3.3 (v10.4.0 was one day old
  and skipped), Python 3.13, gitleaks 8.30.1 with the sha256 published in its release.
- The installation and distribution note, item 2, is marked partly settled.
- How the platforms were checked:

  | Platform | How | Result |
  | --- | --- | --- |
  | Windows 11 | locally, `ruff check`, `ruff format --check`, `pytest` | clean, 883 passed |
  | Linux | locally, a clean clone in a `python:3.13` container, `uv sync --locked`, the same commands | clean, 882 passed, 1 skipped (Windows-only test) |
  | gitleaks | locally, a clean clone in the gitleaks 8.30.1 container, full history | 376 commits, no leaks |
  | Workflow file | `actionlint` 1.7.7 in a container | no findings |
  | ubuntu, windows, macos on GitHub | the first run of the workflow on this branch, a push of commit `9819f9a` | all four jobs green: ubuntu and macos 882 passed, 1 skipped; windows 883 passed; gitleaks 366 commits, no leaks |

  The Linux check found two tests failing on POSIX; they were fixed first in the session
  `2026-11-21-implementation-2`.

## Decisions
1. **gitleaks runs as a pinned binary, not through `gitleaks-action`.** It is the tool already used
   for the history scan, it brings no third-party action code and needs no token; the action would be
   shorter but adds an external dependency with its own licence, and on a pull request it scans only
   the pull request's commits.
2. **macOS is in the matrix from the start.** No local route exists, and the first run on this
   branch happens before the merge, so a red macOS is known before CI reaches `development`.
3. **Exact version tags, not commit SHAs.** Readable and easy to update; SHAs would protect against a
   moved tag at the cost of both.
4. **`pytest` runs on three systems, gitleaks on one.** The scan reads the history, which does not
   depend on the operating system.

## Open questions
- None.

## Next steps
1. Merge `chore/ci-pipeline` into `development`.
2. The platforms the project claims to support, open question 2 of the installation and distribution
   note, can now be answered with CI evidence for ubuntu, windows and macos.
3. A maintenance session on when the pipeline runs, raised by the owner after the merge: gitleaks on
   every push, but tests not on every push of an unfinished branch and not on changes to documentation
   only. Alternatives to weigh: tests on every branch as now; tests only on push to `development`, which
   moves the check after the merge; a manual `workflow_dispatch` run on a branch before its merge; a
   commit-message marker that skips tests. For documentation-only changes, `examples/` is read by the
   tests and cannot count as documentation, gitleaks then needs its own workflow file because a path
   filter applies to the whole workflow, and a path-filtered workflow leaves a required status check
   pending if branch protection is turned on later. The macOS runner is the slowest and GitHub already
   warns of queue times on it.

## References
- Branch: `chore/ci-pipeline`
- Added: `.github/workflows/ci.yml`
- Changed: `docs/architecture/notes/2026-08-19-installation-and-distribution.md`
- Session: `2026-11-21-implementation-2` (the artifact-path tests made platform-independent)
