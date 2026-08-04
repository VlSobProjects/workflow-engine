# Session: ADR 005 draft for component loading and plugins

## Type
architecture

## Goal
Start the simplest architecture backlog item by drafting an ADR for deterministic component loading and plugin registration.

## Completion criteria
- One new Draft ADR is created with alternatives, trade-offs, and change cost.
- The ADR captures concrete implementation steps.
- The ADR defines testing steps, exact success criteria, and test data.

## Scope boundaries
Architecture discussion and documentation only. No production code changes.

## Status
completed

## Result

Draft ADR 005 was created and refined to formalize deterministic plugin loading before workflow execution.

Delivered in ADR 005:

- Decision for hybrid plugin bootstrap: local manifest modules + external entry-point plugins.
- Three alternatives with trade-offs and cost profile.
- Consolidated architecture decisions required for loading boundary.
- Step-by-step implementation plan.
- Test plan, measurable success criteria, and concrete test data set.

## Decisions

- Treat plugin loading as bootstrap concern, not import side effect at call sites.
- Keep decorator registries unchanged; add deterministic loading phase before node construction.
- Support two plugin channels: explicit local manifest and external package entry points.

Related ADRs:

- [ADR 004 session bootstrap and configuration snapshot](../adr/adr-004-session-bootstrap-and-config-snapshot.md)
- [ADR 005 component loading and plugin registration model](../adr/adr-005-component-loading-and-registration.md)

## Open questions

- Whether entry-point loading should be all discovered plugins or allow-listed plugin names.
- Whether strict mode should fail on duplicate component names across plugins.
- Version-compatibility policy between core and external plugins.

## Next steps

1. Finalize open questions in ADR 005 discussion.
2. If approved, move ADR 005 to `Implementing` and start feature branch.
3. Implement bootstrap loader and tests per ADR 005 implementation notes.

## References

- Branch: `development`.
- Updated documents: `docs/adr/adr-005-component-loading-and-registration.md`, `docs/adr/README.md`.
- Session closed as architecture-only scope. Implementation is intentionally moved to a separate implementation session and feature branch.
