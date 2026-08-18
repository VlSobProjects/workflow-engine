# Git workflow

This document defines the branch structure and the rules for working with git in this repository.

## Long lived branches

- `main` — the stable line. It holds work that is known to work and is the line that gets tagged.
- `development` — the integration line. Feature branches are merged here, and this is where an ADR is frozen.

Never commit directly to `main`.
Direct commits to `development` are allowed only for opening or editing a Draft ADR together with its
registry row, other ADR status changes, the ADR registry, architecture notes and their registry
(`docs/architecture/notes/`), and trivial corrections such as typos.

## Branch categories

Every branch is created from `development` and lives in a category folder:

- `feature/` — new functionality
- `fix/` — defect fixes
- `refactor/` — structural change without behaviour change
- `docs/` — documentation, rules and ADR text outside implementation
- `test/` — test only changes
- `chore/` — tooling, dependencies, configuration
- `poc/` — experiments

## Naming

- Format: `<category>/<short-name>`
- ADR driven work: `<category>/adr_<number>-<short-name>`, for example `feature/adr_002-node-composition`
- Use lowercase ASCII and hyphens inside the short name.
- The name states what the branch does, not who works on it.

The `adr_` token is what marks a branch as ADR driven. There are no separate ADR categories.

## Working rules

- One branch per task. If the task splits, create a new branch instead of widening the current one.
- Branch from `development`, not from another task branch, unless the work genuinely depends on it.
- Delete the branch after it is merged, except for a `poc/` branch that is deliberately kept as a reference implementation.
- Keep the branch focused: unrelated changes belong to their own branch and category.

## Merging

- Task branches are merged into `development`.
- `development` is merged into `main` when the state is stable and worth marking as such.
- A `poc/` branch is never merged into `development`.
- Before merging into `development`, the required tests and the linter must pass.
- When merging into `development`, update every registry the branch touched: the ADR registry
  (`docs/adr/README.md`), the sessions registry (`docs/sessions/README.md`), and the architecture notes
  registry (`docs/architecture/notes/README.md`).

## Working tree hygiene

Every file in the working tree must be in one of two states: tracked by git, or ignored.
A file that is neither committed nor ignored is an unresolved question, not a normal state.

Check this regularly, and always before finishing a task:
- inspect the working tree for untracked and uncommitted files,
- for each one, decide whether it belongs in the repository or in `.gitignore`,
- when the answer is not obvious, raise the question with the user instead of deciding silently.
- do not finish a task or session with uncommitted tracked changes unless the user explicitly accepts
  ending uncommitted.

Once a remote exists, also check for commits that were never pushed and raise them the same way.

### What belongs in `.gitignore`
Propose adding anything that is useful only on the local machine:
- test and tool caches, coverage output, build artifacts,
- local environment and virtual environments,
- IDE and editor settings that are personal rather than shared,
- local helper scripts and scratch files,
- generated output that can be reproduced.

Never commit secrets, credentials or local configuration containing them.

## ADR specifics

Branch creation and the freeze point for ADR work are defined in `docs/adr/process.md`.
