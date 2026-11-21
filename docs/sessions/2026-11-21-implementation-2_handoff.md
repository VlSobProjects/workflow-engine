# Session 2026-11-21-implementation-2

## Type
`implementation`

## Goal
Make the two artifact-path tests of `tests/test_state.py` that fail on Linux pass on every platform, so
the first run of the CI pipeline can be green.

## Completion criteria
- `test_get_artifact_absolute_path` and `test_get_artifact_relative_path` use a path outside the
  artifacts root that is absolute on any operating system.
- `uv run ruff check .` clean and `uv run pytest` green on Windows.
- The same commands green on Linux, in a clean clone inside a `python:3.13` container with
  `uv sync --locked`.
- No change to the engine code.

## Scope boundaries
- No CI pipeline: that is the session `2026-11-21-maintenance-1` on `chore/ci-pipeline`.
- No macOS run: no local route exists; macOS is first checked by the CI pipeline.
- Other tests that hold a `C:/...` literal are not touched: they use it as an opaque value and pass on
  Linux.

## Status
`completed`

## Result
- Both tests rejected `"C:/non_existent_artifact.txt"` as an absolute path outside the artifacts
  root. On POSIX the string is a relative path under a directory named `C:`, which resolves inside the
  artifacts root, so the engine correctly accepted it and the tests failed. They now use
  `tmp_path / "outside_artifact.txt"`: `tmp_path` is the work directory, the artifacts root is
  `tmp_path/artifacts`, so the path is absolute and outside the root on any system.
- Checked on Windows 11: ruff clean, format check clean, pytest 883 passed.
- Checked on Linux, a clean clone in a `python:3.13` container with the change applied and
  `uv sync --locked`: ruff clean, format check clean, pytest 882 passed, 1 skipped. The skip is the
  Windows-only test in `tests/test_json_storage.py` (rename refused over an open file).
- Before the change the same Linux run gave 2 failed, 880 passed, 1 skipped.

## Decisions
1. **The defect is in the tests, not in the engine.** The engine's containment check resolves both
   the target and the artifacts root, and a POSIX system has no drive letters; accepting `C:/x` as a
   relative name there is correct.
2. **Linux is checked locally through a container before CI exists.** It turns the first CI run from a
   guess into a confirmation for Linux and Windows; macOS remains unverified until that run.

## Open questions
- None.

## Next steps
1. The session `2026-11-21-maintenance-1` on `chore/ci-pipeline`: the GitHub Actions workflow with
   ruff, pytest and gitleaks on every push and pull request, pytest on ubuntu, windows and macos.

## References
- Branch: `test/artifact-path-cross-platform`
- Changed: `tests/test_state.py`
