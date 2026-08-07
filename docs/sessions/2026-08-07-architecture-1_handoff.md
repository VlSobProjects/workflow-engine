# Session note

## Type
architecture

## Goal
Review ADR 006 implementation in `feature/adr_006-data-flow-between-nodes` and decide whether it can be moved to Accepted.

## Completion criteria
- Implementation is checked against ADR 006 decision and consequences.
- Critical deviations are listed with concrete remediation guidance.
- Acceptance verdict is explicit.

## Scope boundaries
- Architecture review only.
- No production code edits in this session.

## Status
completed

## Result
Architecture review was completed for the current ADR 006 implementation state. Earlier blockers were
rechecked and closed for architecture-readiness of the next phase. The branch is now ready to move to
test implementation (component tests for new behavior and the ADR 006 e2e folder-scan scenario).

## Decisions
- ADR 006 is **not ratified yet** and will not move to Accepted before:
  - tests for new components/contract surfaces;
  - end-to-end test for folder scanning and resume equivalence scenario.
- Artifact responsibility split is accepted and documented:
  - function level may enforce strict pre-write checks and fail early;
  - engine level must keep `state.artifacts` factual and record conflicts in `state.artifact_events` for returned artifacts.

## Open questions
None.

## Next steps
1. Implement tests for new/changed components:
   - `StateReadOnlyView` artifact path normalization and error mapping;
   - `StateModel` artifact conflict events and `param_writes` error paths;
   - artifact function behavior under valid and conflicting inputs.
2. Implement ADR 006 e2e acceptance test:
   - folder scan loop;
   - file/folder branching;
   - artifact generation;
   - mid-loop resume with equivalence of final params/artifacts to straight run.
3. After green tests and scenario validation, run final architecture ratification pass for ADR 006.

## References
- Branch: `feature/adr_006-data-flow-between-nodes`
- Base comparison: `development...HEAD`
- ADR: `docs/adr/adr-006-data-flow-between-nodes.md`
- Key files reviewed:
  - `src/workflow_engine/models/state.py`
  - `src/workflow_engine/output.py`
  - `src/workflow_engine/collection_param_handlers.py`
  - `src/workflow_engine/actions/action_nodes.py`
  - `src/workflow_engine/actions/base_functions.py`
  - `src/workflow_engine/actions/modify_param_functions.py`
  - `src/workflow_engine/engine.py`
  - `src/workflow_engine/actions/create_artifact_functions.py`
  - `src/workflow_engine/bootstrap/plugin_manifest.py`
  - `examples/colect_file_info_workflow.json`
