# Implementation rules

These rules apply to every code change.

## 1. Before changing code
Read the code and the tests that surround the change.
Understand how the piece is used before editing it.
Detailed attention to the context and potential side effects.
Before changing any code, give a short explanation and wait for the confirmation or questions for details.

## 2. Size of a change
Keep a change small enough to review in one pass.
Preserve existing public behaviour unless the task explicitly requires changing it.
Do not refactor code that the task does not require.

## 3. Style
Follow the conventions already present in the code.
Prefer explicit and simple code over clever code.
Use type annotations on public functions, classes and registry entries.
Comment only what is not obvious from the code.
Do not commit commented out code or dead code.

## 4. Automated checks
Ruff is the only mandatory automated checker, used for both linting and formatting.
It is configured in `pyproject.toml`; the configuration is part of the project, not a local setting.
A type checker is not in use yet. Adopting one is an architectural decision and needs its own ADR.

## 5. The command line is the source of truth
Verification means running the tools from the command line.
Warnings shown by an IDE panel are a hint and may be stale; they never replace a command line run.

## 6. Automatic fixes are reviewed, never trusted
Never apply automatic fixes blindly.
Unsafe fixes are not applied at all.
Removal of an unused import is always reviewed by hand: this project registers functions and actions
through decorators that run at import time, so an import that looks unused may be the only thing that
performs the registration. Deleting it breaks the project silently.

## 7. Tests
Every behaviour change is covered by a test.
Tests run with pytest.
Run the relevant tests and Ruff before merging into `development`, and report what was run.

## 8. Failures are explicit
Validate input at the boundaries of the engine and fail with the project's own exception types.
Do not swallow errors and do not return a silent default in place of an error.

## 9. Path serialization
Persist and expose paths in POSIX form, not native OS path separators. This keeps config, state and session data portable across platforms and matches ADR 008: `docs/adr/adr-008-runtime-directory-and-default-path-policy-for-v1.md`.

## 10. Dependencies
Prefer the standard library.
A new dependency must earn its place: it has to solve a real problem better than a small local
implementation, be maintained, and have an acceptable licence.
It requires explicit approval, is declared in `pyproject.toml`, and development tools are declared
separately from runtime dependencies.

## 11. Documentation of a change
A change that makes `README.md` or `docs/architecture/overview.md` inaccurate carries the correction
in the same branch. The rule and its scope live with the other merge preconditions in
`docs/processes/git-workflow.md`.

## 12. Registration and dynamic behaviour
Registries are populated at import time. Keep that mechanism explicit and visible.
When adding a module that registers something, make sure it is actually imported by the code that
needs it, rather than relying on an accidental import.
