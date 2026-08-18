# Session note

## Type
architecture

## Goal
Correct ADR 009 metadata model after identifying a mismatch between developer docstrings and operator help needs.

## Completion criteria
1. Resolve the documentation-domain mismatch for `Action` detailed help.
2. Clarify per-component-type sources for operator-facing detailed help.
3. Record the correction in ADR 009 change log.

## Scope boundaries
- ADR 009 text only.
- No implementation code changes.
- No status transition in this session.

## Status
completed

## Result
ADR 009 now distinguishes developer documentation from operator-facing workflow authoring guidance and defines type-specific sources for detailed help.

## Decisions
1. `help-component` is an operator workflow-authoring surface, not an implementation/inheritance surface.
2. Action detailed help must come from explicit action metadata that describes node usage (`action_parameters`, behavior notes, example shape), not class docstrings.
3. Function and validator detailed help combines signature with doc-derived parameter descriptions (`Args`), while `Returns` is optional and not required for v1 operator help.
4. JSON detailed component shape keeps stable mandatory keys without requiring `returns` as mandatory.

## Open questions
1. Exact metadata field shape for action usage examples (`example`, `examples`, or structured `node_template`).

## Next steps
1. In implementation session, define concrete metadata structures for action/function/validator/guard/codec detail payloads.
2. Implement extraction and CI quality gates according to corrected ADR 009 rules.

## References
- ADR: `docs/adr/adr-009-operator-help-and-component-introspection-contract.md`
- Branch: `feature/adr_009-operator-help-and-component-introspection-contract`
