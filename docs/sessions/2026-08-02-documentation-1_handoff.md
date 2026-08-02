# Session: project rules and documentation system

## Type
documentation

## Goal
Establish the rules and the documentation system that govern how this project is worked on, and bring the
repository into a clean state under those rules.

## Completion criteria
- The rule documents exist and are agreed.
- The documentation structure and its entry points exist.
- The repository has no file that is neither tracked nor ignored.
- Lint, format and tests pass from the command line.

## Scope boundaries
No feature work. The unfinished engine code carried over from earlier work was committed as is, apart from
defects that made a module impossible to import.

## Status
completed

## Result

The documentation system is in place:

- `AGENTS.md` and `.github/copilot-instructions.md` route by task type and carry no rules of their own.
- `docs/rules/` holds general, ADR, implementation and documentation rules.
- `docs/adr/` holds the ADR registry, template, format and lifecycle.
- `docs/sessions/` holds the session registry, template and notes.
- `docs/processes/git-workflow.md` holds the branch model.
- `docs/architecture/overview.md` is reserved for the current architecture and is not written yet.

The repository was brought into a clean state:

- `master` was renamed to `main`, and `development` was created.
- IDE settings are no longer tracked, and the generated PyCharm sample script was removed.
- Packaging, pytest and Ruff are configured, the backport packages were dropped, and the development tools
  moved out of the runtime dependencies.
- The tests run from the repository root and no longer depend on the working directory.
- Ruff reports no findings, formatting is applied and all tests pass.

## Decisions

- Rules are short and binding, with details linked rather than repeated.
- An ADR is frozen only after implementation and testing, so a decision that is still open is edited in
  place instead of being superseded.
- ADR drafts live on `development`; POC and implementation work happen in their own branches.
- Documentation may only be created inside a closed document map.
- Session note names carry no description, so the session registry is the only index.
- Ruff is the only mandatory checker for now. Adopting a type checker is an architectural decision and
  needs its own ADR.
- The exception architecture will add context to errors as they travel up. See ADR 001.

## Open questions

- Whether `file_size` in `file_info_functions` was meant to be registered like its neighbours.
- Whether the repeated response building in `sart_engine` should be extracted.

## Next steps

1. Capture the decisions that are already implemented as ADRs, and write `docs/architecture/overview.md`.
2. Finish and test the engine code that is currently unfinished on `development`.
3. Take ADR 001 on the exception architecture from draft to implementation.
4. Unify the validation utilities once ADR 001 is settled.
5. Revisit adopting a type checker as its own ADR.

## References

- Branch: `development`, with the tooling work merged from `chore/ruff-and-pyproject-configuration`.
- Related ADR: 001 exception architecture, draft.
- This session created the documents listed in the result section.
