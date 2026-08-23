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

## Commit messages

A commit message is written in English and states why the change was made.
What changed is already in the diff.

Form:

```
<type>: <what the commit does, one line>

<body: the reason, the alternative that was rejected, the consequence a reader cannot see in the diff>

Verified: <the commands that were run and their result>
```

- `<type>` is the branch category of the work in its commit form: `feat`, `fix`, `refactor`, `docs`,
  `test`, `chore`, `poc`. A `feature/` branch commits as `feat:`.
- The subject is one line, lower case after the type, without a trailing period, at most 80 characters.
  It names what the commit does, not which files it touched.
- The body is wrapped at 100 characters and written as prose. Use a list only when the change has
  several independent parts.
- `Verified:` is required by every commit that touches code, and names what was actually run, for
  example `Verified: uv run ruff check . clean; uv run pytest 364 passed.`
  A commit that touches no code carries no such line.
- A commit whose subject already says everything needs no body: registering a session, a registry
  row, a typo.

A multi line message is written to a file and committed with `git commit -F <file>`, to keep the
shell's quoting out of the message.

The message is shown to the user before the commit is made: see `docs/rules/general-rules.md` §12.

## Merging

- Task branches are merged into `development`.
- A merge commit states what the branch delivers: `Merge <branch>: <what the branch delivers, one line>`.
  It carries no body; the reasoning is in the commits of the branch itself.
- `development` is merged into `main` when the state is stable and worth marking as such.
- A `poc/` branch is never merged into `development`.
- Before merging into `development`, the required tests and the linter must pass.
- A `feature/`, `fix/` or `refactor/` branch synchronizes the documentation its change made
  inaccurate, in the same branch: `README.md` for anything an operator or a calling program sees,
  the walkthrough in `examples/` for anything one of the shipped templates does, and
  `docs/architecture/overview.md` for anything the architecture description states. A change that
  affects neither needs no documentation edit; a change that does is not finished without one.
- When merging into `development`, update every registry the branch touched: the ADR registry
  (`docs/adr/README.md`), the sessions registry (`docs/sessions/README.md`), the architecture notes
  registry (`docs/architecture/notes/README.md`) and the scenarios registry
  (`docs/architecture/scenarios/README.md`).

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
