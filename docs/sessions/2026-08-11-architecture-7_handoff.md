# Session note

## Type
architecture

## Goal
Refine ADR 009 to define a dedicated help-contract module, explicit acceptance boundaries, and CLI wiring options.

## Completion criteria
1. Add module structure for operator-help contract assembly.
2. Define clear ADR acceptance boundaries for freeze.
3. Record CLI wiring options and recommended path.

## Scope boundaries
- ADR 009 text only.
- No implementation code changes.
- No ADR status transition.

## Status
completed

## Result
ADR 009 now includes a dedicated help-contract module architecture, WorkflowNode-oriented detail schema, explicit CLI coupling boundaries, CLI wiring alternatives, and concrete acceptance boundaries for moving to Accepted.

## Decisions
1. Contract assembly must live in a dedicated `help_contract` module with DTO models, per-type adapters, builder, and renderers.
2. Action detailed help is standardized around WorkflowNode authoring artifacts (`node_template`, parameter groups, transition hints, examples).
3. CLI must consume builder DTOs and avoid direct registry-formatting logic in command handlers.
4. Thin-command wiring is the recommended v1 integration path; service-based wiring remains a valid follow-up optimization.

## Open questions
1. Final field naming for action examples (`examples` vs structured `node_template` variants) at implementation time.

## Next steps
1. Implement the `help_contract` module and connect CLI use-cases to it.
2. Add contract tests that enforce acceptance boundaries defined in ADR 009.

## References
- ADR: `docs/adr/adr-009-operator-help-and-component-introspection-contract.md`
- Branch: `feature/adr_009-operator-help-and-component-introspection-contract`
