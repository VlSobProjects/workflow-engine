# Session note

## Type
architecture

## Goal
Settle ADR 006 open questions and move the ADR from Draft to Implementing with an explicit contract.

## Completion criteria
- The open questions in ADR 006 are resolved into concrete contract rules.
- ADR 006 status is moved to Implementing with an active branch.
- ADR registry and session registry are updated.

## Scope boundaries
- Architecture and documentation only.
- No production code changes.

## Status
completed

## Result
ADR 006 was moved to Implementing. The data flow contract is now explicit: `state.params` stays the only
typed persisted bus, actions publish typed parameter write sets, only the engine applies writes, and state
is persisted on every node turn.

Post-session clarifications were added without changing the decision direction: parameter writes are
runtime action output (not workflow mapping DSL), apply semantics are declarative (`set`, `replace`,
`append`), and engine-side contract errors are explicit.

## Decisions
- Keep a flat parameter namespace and make overwrite explicit through `allow_overwrite=true`.
- Separate channels in node output: `output_text` for diagnostics, typed workflow data in `param_writes`.
- Remove transient output-to-output parameter propagation.
- Keep guards read-only over resolved references; do not expose mutable state.
- Keep artifact registration mandatory in `state.artifacts`.
- Include only minimal loop guardrail in ADR 006 and defer full loop policy to a separate ADR.
- Reshape `FunctionsAction`, `PopFromQueue`, and `CreateArtifactActionWithContent` under the new contract.
- Exclude `ForEachOutputParameterNode` from ADR 006 scope; treat it as a separate topic.
- Keep `param_writes` as part of `ActionNodeOutput`, produced by action code at runtime, not declared in
  `WorkflowNodeModel` as a second mapping layer.
- Keep write instructions declarative data (no lambda/callable contract at engine boundary).
- Use minimal update modes in the first implementation: `set`, `replace`, `append`.

## Open questions
- Final serialization and validation path of `ParamWrite` in persisted state and tests.
- Whether `output.*` references in guards stay for compatibility or are reduced later.
- Which follow-up ADR will own `ForEachOutputParameterNode` semantics.

## Next steps
1. Implement ADR 006 in `feature/adr_006-data-flow-between-nodes`.
2. Update example workflows and add end to end resume coverage for the folder scan scenario.
3. Open a dedicated ADR for full loop termination/retry policy.

## References
- Branch: `development`
- ADR: `docs/adr/adr-006-data-flow-between-nodes.md`
- Registry: `docs/adr/README.md`
