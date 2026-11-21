# Session 2026-11-21-implementation-1

## Type
implementation

## Goal
Make `test_installed_cli_smoke` pass in a fresh clone whose project environment was made by `uv sync`,
which installs no `pip`, as found by the clean-clone check of `2026-11-21-documentation-1`.

## Completion criteria
- The smoke test builds the wheel without needing `pip` in the environment that runs pytest.
- No new dependency; the test still builds, installs and calls the command as before.
- `uv run ruff check .` is clean and `uv run pytest` passes in the working copy and in a fresh clone
  whose project environment holds no `pip`.

## Scope boundaries
- No engine code changes.
- No CI pipeline: that is its own maintenance session.
- The test's need for network access (the build backend and the engine's dependencies are fetched
  by `pip wheel`) is kept as it was.

## Status
`completed`

## Result
- `tests/test_install_smoke.py` creates the smoke environment first and builds the wheel with that
  environment's own `pip`, which `venv` installs; the project interpreter is no longer called, and
  its unused `sys` import is gone.
- Working copy: ruff clean, `uv run pytest` 883 passed. Fresh clone with no `pip` in the project
  environment: `uv run pytest` 883 passed, where it gave 882 passed and 1 failed before.

## Decisions
1. **The wheel is built by the smoke environment's `pip`.** It is created with `pip` anyway, so the
   test now depends only on what it makes itself. Alternatives rejected: `uv build` would tie the
   test to `uv` being on `PATH`; adding `pip` to the dev dependency group adds a dependency to cover
   a symptom.

## Open questions
- None.

## Next steps
1. The owner pushes, switches the repository to public, sets its description and topics, and turns
   on secret scanning and push protection.
2. A `notice` to JobSearch as a draft on the desk, answering EX-44.
3. The CI pipeline session on `chore/ci-pipeline`.
4. On merge: add this session's registry row on `development`.

## References
- Branch: `fix/install-smoke-without-project-pip`
- Changed: `tests/test_install_smoke.py`
- Found by: `2026-11-21-documentation-1`
