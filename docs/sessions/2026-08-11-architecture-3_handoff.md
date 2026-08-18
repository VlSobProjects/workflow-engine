# Session note

## Type
architecture

## Goal
Refine ADR-008 so it captures the runtime root, default path policy, config discovery order, and error semantics needed for implementation.

## Completion criteria
1. Resolve the remaining ADR-008 ambiguities around runtime root, config discovery and override precedence.
2. Capture the clarified decisions in the ADR text.
3. Close the session note with the resolved decisions and implementation guidance.

## Scope boundaries
- ADR-008 only.
- No code changes unless they are required to validate an architecture decision.
- No new ADR creation.

## Status
completed

## Result
ADR-008 now defines a concrete v1 policy for the runtime root, work directory, JsonStorage directory, config discovery, override precedence, path serialization and setup/config error handling.

## Decisions
1. Use `<cwd>/.workflow-engine/` as the default runtime root and default config root.
2. Keep `work_dir` equal to the runtime root, with sessions under `<work_dir>/sessions/<session_id>/`.
3. Use `<runtime_root>/json-storage/` as the default JsonStorage directory; if only `--work-dir` is provided, the default storage path becomes `<work_dir>/json-storage/`, while `--storage-dir` overrides that location directly and becomes the storage root directory itself.
4. Resolve config discovery in this order: explicit `--config`, `<cwd>/.workflow-engine/workflow_engine_config.json`, `<user_config_dir>/.workflow-engine/workflow_engine_config.json`, then create a default config at `<runtime_root>/workflow_engine_config.json`.
5. Give CLI options `--work-dir` and `--storage-dir` the highest precedence, followed by environment variables `WE_WORK_DIR` and `WE_STORAGE_DIR`, then config values.
6. Raise `WorkflowConfigurationError` for config lookup, config creation and directory-creation failures so the CLI can report them consistently.

## Open questions
None.

## Next steps
1. Implement ADR-008 in the feature branch once the work begins.
2. Add command-level tests for defaults, overrides, config precedence and setup failures.

## References
- ADR: `docs/adr/adr-008-runtime-directory-and-default-path-policy-for-v1.md`
- Branch: `development`
