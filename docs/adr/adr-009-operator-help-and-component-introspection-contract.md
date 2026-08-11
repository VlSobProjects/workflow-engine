# ADR 009: Operator help and component introspection contract

## Status
Draft

## Active branch
—

## Context

Phase 1 must let an operator discover what can be used in workflow definitions:
actions, functions, guards, and codecs. Core registries already expose part of this data, but there is no
frozen operator contract for:

- list versus detailed output;
- per-component detail fields;
- how non-registry guard kinds are shown;
- stable machine-readable shape for tooling.

Without this contract, help output stays ad hoc and hard to automate.

## Decision

Define one help/introspection contract for CLI v1:

1. Surfaces:
   - `help-components` list by type: `actions`, `functions`, `validators`, `guards`, `codecs`;
   - `help-component --type <type> --name <component>` for detailed view.
2. Output shape:
   - text and json modes share the same semantic fields (`name`, `type`, `description`, `parameters`,
     `source`, `notes`).
3. Source of truth:
   - registries for actions/functions/validators/codecs;
   - explicit static catalog for guard kinds that are not registry-backed (`equals`, `contains`, groups, etc.).
4. Scope:
   - report component metadata and usage contracts only;
   - do not perform runtime validation or workflow linting in this command.

## Alternatives considered

### A. Keep generic `--help` text only
Pros: lowest effort.  
Cons: not enough for workflow authoring; no discoverability of dynamic registrations.

### B. Documentation-only lists in markdown
Pros: easy to edit.  
Cons: drifts from runtime registrations; cannot represent external modules reliably.

### C. Runtime introspection contract (chosen)
Pros: reflects actual loaded components; automatable; stable operator guidance surface.  
Cost: define metadata schema and fill gaps for non-registry guards.

## Consequences

- A guard catalog abstraction is required for operator-facing descriptions.
- Docstrings and metadata quality become release-relevant for built-ins.
- External module registrations become visible at runtime through the same interface.

## Related ADRs

- ADR 005 component loading and plugin registration model (Accepted).
- ADR 007 CLI contract and session lifecycle for v1 (Draft).

## Implementation notes

Planned branch when status moves beyond Draft:
- `feature/adr_009-operator-help-and-component-introspection-contract`

Minimum v1 implementation:
- list and detail commands for all component types via `help-components` and `help-component`;
- deterministic JSON schema;
- at least one test with external module registration visibility.

## Change log

- Initial draft opened from phase 1 architecture planning session.
