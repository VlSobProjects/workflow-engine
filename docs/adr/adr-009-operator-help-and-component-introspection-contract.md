# ADR 009: Operator help and component introspection contract

## Status
Implementing

## Active branch
feature/adr_009-operator-help-and-component-introspection-contract

## Context

Phase 1 must let an operator discover what can be used in workflow definitions:
actions, functions, guards, and codecs. Core registries already expose part of this data, but there is no
frozen operator contract for:

- list versus detailed output;
- per-component detail fields;
- how non-registry guard kinds are shown;
- stable machine-readable shape for tooling.

Without this contract, help output stays ad hoc, metadata quality drifts, and automation remains brittle.
The current draft also needs a clear policy for internal vs external component metadata quality and for how
acceptance tests validate the contract.

## Decision

Define one help/introspection contract for CLI v1:

1. Surfaces:
   - `help-components` list by type: `actions`, `functions`, `validators`, `guards`, `codecs`;
   - `help-component --type <type> --name <component>` for detailed view.
2. Two-level description model:
   - `summary`: short one-line operator description for list output;
   - `description`: detailed usage description for detail output, including parameter meaning and return semantics.
3. Source of truth:
   - registries for actions/functions/validators/codecs;
   - explicit static catalog for guard kinds that are not registry-backed (`equals`, `contains`, groups, etc.).
4. Metadata ownership and enforcement:
   - internal components must provide non-empty `summary` and non-empty detailed docstring-based description;
   - v1 enforcement point is test/CI quality gates for internal components (not runtime hard-fail);
   - external components are best-effort; if metadata is missing, help output must state that the description
     is not provided by the external component.
5. JSON contract stability:
   - `help-components` JSON response includes top-level `contract_version` and `components`, where
     `components` contains normalized type keys (`actions`, `functions`, `validators`, `guards`, `codecs`);
   - `help-component` JSON response includes top-level `contract_version` and `component`;
   - detailed component object keeps stable key names: `name`, `type`, `summary`, `description`,
     `parameters`, `returns`, `source`, `notes`;
   - additive extension is allowed only via new optional fields; existing key names and structural nesting are stable.
6. Scope:
   - report component metadata and usage contracts only;
   - do not perform runtime validation or workflow linting in this command.
7. Testing policy for this ADR:
   - operator-contract and e2e acceptance tests must use core registered components, not test-local extra
     registrations;
   - if a required component is missing, implement it in core registration surface rather than registering
     it only in tests.
8. Core component generality policy:
   - when replacing test-local helpers with core components, design the component API to be reusable and
     domain-neutral rather than scenario-specific;
   - each newly introduced core helper in this scope must be justified by at least two realistic workflow
     scenarios.

## Alternatives considered

### A. Keep generic `--help` text only
Pros: lowest effort.  
Cons: not enough for workflow authoring; no discoverability of dynamic registrations.

### B. Docstring-only metadata (summary and details from `__doc__`)
Pros: low implementation cost; no extra metadata field.
Cons: weak enforceability for short list output, inconsistent quality, and no explicit ownership signal in registration.

### C. Central static metadata catalog
Pros: explicit and consistent metadata in one place.
Cons: high drift risk against runtime registrations and plugin loading, additional maintenance burden.

### D. Hybrid runtime contract (chosen)
Pros: reflects actual loaded components; keeps short metadata explicit at registration point; reuses docstrings
for detailed guidance; automatable and stable for tooling.  
Cost: registry metadata extension, metadata backfill for internal components, and CI contract checks.

## Consequences

- A guard catalog abstraction is required for operator-facing descriptions.
- Internal component metadata quality (`summary` + docstring details) becomes release-relevant.
- External module registrations remain visible through the same interface, with explicit missing-metadata reporting.
- Acceptance tests for this ADR must avoid test-only component registrations to keep the contract aligned with
  production core surfaces.
- Existing core components require metadata backfill work before freeze.
- Promoting test-only helpers into core requires API design discipline and at least one additional realistic
  usage scenario to prove reusability.

## Related ADRs

- ADR 005 component loading and plugin registration model (Accepted).
- ADR 007 CLI contract and session lifecycle for v1 (Draft).

## Implementation notes

Planned branch when status moves beyond Draft:
- `feature/adr_009-operator-help-and-component-introspection-contract`

Minimum v1 implementation:
- list and detail commands for all component types via `help-components` and `help-component`;
- deterministic JSON response shape with stable key names and structural nesting;
- at least one test with external module registration visibility.
- metadata quality gate test for internal components:
  - non-empty `summary`;
  - non-empty detailed docstring;
  - parameter names from signature covered in detailed description.
- replace test-local helper registrations used by operator/e2e acceptance tests with reusable core helpers,
  validated by at least two realistic workflow scenarios.

## Change log

- Initial draft opened from phase 1 architecture planning session.
- Refined decision with hybrid metadata ownership, explicit internal/external enforcement policy, stable JSON
  contract keys, and ADR-specific testing policy forbidding test-local component registration in operator/e2e
  acceptance coverage.
- Added a core-component generality policy for migrating test-local helpers into reusable production
  registrations, with required validation by at least two realistic scenarios.
- Status changed from `Draft` to `Implementing`; implementation branch assigned.
