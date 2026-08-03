# Session: ADR 003 boundary clarification

## Type
architecture

## Goal
Align ADR 003 with the agreed architecture boundary between run workspace and persistence.

## Completion criteria
- ADR 003 states that `work_dir` is mandatory for a run.
- ADR 003 states that run bootstrap ownership is in engine-level orchestration.
- ADR 003 includes concrete implementation notes for the next implementation session.

## Scope boundaries
Only ADR 003 wording and decision clarity. No production code changes.

## Status
completed

## Result

ADR 003 was updated to reflect the agreed model:

- The application remains filesystem-dependent for run workspaces.
- `work_dir` is mandatory in `StateModel` for all backend types.
- Persistence and run bootstrap responsibilities are separated.
- Until a Session abstraction exists, run start orchestration is owned by `engine.py`.

The ADR now includes a concrete implementation sequence for tomorrow's implementation work.

## Decisions

- Keep `work_dir` as a required run invariant and persisted state field.
- Move run start (`start_workflow` responsibility) to engine-level orchestration.
- Keep persistence backends medium-focused, with backend-specific constructor dependencies.

Related ADR: [ADR 003 persistence and workspace](../adr/adr-003-persistence-and-workspace.md).

## Open questions

- Engine boundary for workflow input: file path, data payload, or both.
- `work_dir` validation strictness when loading state from non-file backends.
- Whether to keep `Storage.start_workflow` as a temporary compatibility wrapper.

## Next steps

1. Implement engine-level start API in `src/workflow_engine/engine.py`.
2. Refactor storage contract to persistence-only responsibilities.
3. Adapt `JsonStorage` and tests to the new start flow.
4. Draft Session abstraction ADR after implementation stabilizes.

## References

- Branch: `development`.
- Updated document: `docs/adr/adr-003-persistence-and-workspace.md`.
