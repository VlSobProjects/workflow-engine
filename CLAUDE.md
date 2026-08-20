# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project rules routing

This repository uses task-scoped documentation. `AGENTS.md` is the entrypoint. Read only what the
current task needs:

- Always: `docs/rules/general-rules.md`
- Implementation work: `docs/rules/implementation-rules.md`
- Architecture changes: `docs/rules/adr-rules.md`, `docs/adr/README.md`, `docs/adr/process.md`
- Architecture ideas not yet decided: `docs/architecture/notes/README.md` (capture at any moment;
  reviewed during architecture work)
- Documentation work: `docs/rules/documentation-rules.md`
- Git and branches: `docs/processes/git-workflow.md`
- Current architecture: `docs/architecture/overview.md`
- Session notes: `docs/sessions/README.md` — every new session follows the lifecycle protocol there;
  every session note copies the structure of `docs/sessions/template.md`

Do not read unrelated docs, and create documents only inside the map defined in
`docs/rules/documentation-rules.md`. Ad hoc documents and summaries are forbidden.

## Non-negotiable rules (from docs/rules/)

- All committed artifacts are in English: code, comments, commits, branch names, docs. The
  conversation language with the user is free.
- Never commit to `main`. Branch from `development` as `<category>/<short-name>`
  (`feature/`, `fix/`, `refactor/`, `docs/`, `test/`, `chore/`, `poc/`); ADR-driven work uses
  `<category>/adr_<number>-<short-name>`. Task branches merge into `development`.
- No scope creep: change only what the task requires; do not fix unrelated problems unasked.
- Never write a local path, user name or host name into a committed document; name the role of the
  thing instead. A fact true only on one machine lives outside the repository.
- Before changing code, give a short explanation and wait for confirmation.
- Never commit without showing the full commit message first and waiting: the user confirms it,
  corrects it, or commits themselves. Merge and registry commits included. Present the message as a
  file, so it can be copied and extended without being retyped.
- Architecture is discussed in critical mode: state at least two alternatives, the trade-offs, and
  the cost. Architectural changes happen under an ADR; an accepted ADR is frozen and only superseded.
- A `feature/`, `fix/` or `refactor/` branch also carries the documentation its change made
  inaccurate: `README.md` for what an operator or a calling program sees,
  `docs/architecture/overview.md` for what the architecture description states.
- Working tree hygiene: every file is either tracked or ignored; do not end a task with untracked or
  uncommitted files without raising it.
- Verification means command-line runs of pytest and ruff; report what was actually run. Never claim
  unverified success.
- New dependencies require justification and explicit approval; prefer the standard library.

## Commands

Python 3.13+, managed with `uv` (see `uv.lock`).

```
uv run pytest                                  # all tests
uv run pytest tests/test_engine.py             # one file
uv run pytest tests/test_engine.py::test_name  # one test
uv run ruff check .                            # lint
uv run ruff format .                           # format
```

Ruff is the only mandatory checker (config in `pyproject.toml`, line length 120). There is no type
checker; adopting one requires an ADR. Never auto-remove "unused" imports — registration happens via
decorators at import time, so an unused-looking import may be the only thing registering a component
(`__init__.py` files ignore F401 for this reason).

Prefer the Bash tool (Git Bash) for git and general shell work; use PowerShell only for
Windows-specific tasks, and do not mix the two shells' syntax in one command. For multi-line commit or
PR messages, write the text to a file and use `git commit -F <file>` to avoid shell-quoting pitfalls.

## Architecture

Full description: `docs/architecture/overview.md`. The big picture:

A workflow is a JSON-described graph of nodes. `WorkflowEngine.start_workflow`
(`src/workflow_engine/engine.py`) loads state and definition from storage, builds nodes, and runs
one node at a time until the workflow ends, a node fails, or a node needs input — interactive
actions return a `PresentResponse` to the caller and the engine stops until called again.

- **Node** = one action + an ordered list of guarded transitions. The first transition whose guard
  holds is taken. Targets: another node id, end-of-workflow, or failure under a code.
- **Actions** (`src/workflow_engine/actions/`) perform work and produce one `ActionNodeOutput`;
  errors are values inside that result, not exceptions.
- **Guards** (`src/workflow_engine/transition/guards.py`) are the only predicate concept: they read
  the action result and a read-only state view, which exists to resolve `param.`/`output.`/`artifact.`
  references in their configuration — the predicate function itself gets the resolved values, never
  the state. They return a boolean, and their name is the error code of a node that a `validators`
  entry fails. `validators` in config is sugar that expands to leading failure transitions at build
  time.
- **Registries** (`src/workflow_engine/registry/`): components register at import time via
  decorators — `@register_action`, `@register_function`, `@register_validator`, `@register_type`
  (codecs) — and are looked up by name from configuration. `ComponentLoader`
  (`src/workflow_engine/bootstrap/`) imports built-in core modules first, then configured external
  modules.
- **State** (`src/workflow_engine/models/state.py`): `StateModel` holds everything a resume needs;
  parameter values round-trip through codecs to keep their Python types. `state.params` is an
  engine-managed flat bus written via typed `param_writes`.
- **Storage** (`src/workflow_engine/storage/`): abstract `Storage` with `JsonStorage` as the only
  implementation, keeping `state.json` and `workflow.json` per session; state is written every turn.
  Storage is built per session, not per process.
- **Sessions**: each run owns `<work_dir>/sessions/<session_id>/` with an immutable `session.json`
  record; a resumed session builds storage from its record, not from global config.
- **CLI** (`src/workflow_engine/cli/`): installed as the `workflow-engine` console script; thin
  argparse transport dispatching to use cases. Exit codes: 0 success, 2 paused, 3 failed workflow,
  4 setup/resolution error.
- Paths are persisted in POSIX form regardless of OS (ADR 008).

Architecture decisions live in `docs/adr/`; open architectural questions and ideas not yet decided live
in `docs/architecture/notes/`.