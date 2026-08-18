# ADR 009: Operator help and component introspection contract

## Status
Accepted

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

Without this contract, help output stays ad hoc, metadata quality drifts, and automation remains brittle.
The current draft also needs a clear policy for internal vs external component metadata quality and for how
acceptance tests validate the contract.
During implementation start, a critical mismatch was identified: developer docstrings for `Action` classes
describe implementation and inheritance details, while operator help must explain how to configure workflow
nodes. These are different documentation domains and must not be conflated.

## Decision

Define one help/introspection contract for CLI v1:

1. Surfaces:
   - `help-components` list by type: `actions`, `functions`, `validators`, `guards`, `codecs`;
   - `help-component --type <type> --name <component>` for detailed view;
   - `help-component --type <type>` without a component name for the type-level view: the operator
     description of the component type and the list of its components. `help-components` remains the
     full-list surface for automation and is not changed by this mode.
2. Two-level description model:
   - `summary`: short one-line operator description for list output;
   - `description`: detailed operator usage description for detail output.
3. Source of truth:
   - registries for actions/functions/validators/codecs;
   - explicit static catalog for guard kinds that are not registry-backed (`equals`, `contains`, groups, etc.);
   - catalog entries are named by the configuration key an operator writes, and the catalog also covers
     the `reversed` negation modifier and the `validators` post-condition shorthand, marked by an
     explicit `kind` (`guard`, `modifier`, `shorthand`).
4. Operator-help domain rule:
   - `help-component` describes workflow authoring contract, not implementation/inheritance guidance.
   - Developer-oriented implementation details remain in code-level docs and are not the primary operator-help source.
5. Per-type detail source policy:
   - `actions`: detailed help comes from explicit action metadata focused on node authoring
     (`action_type`, required/optional `action_parameters`, behavior notes, example shape), not from class `__doc__`;
     the metadata is declared at the registration point (`register_action(metadata=...)`);
   - `functions` and `validators`: detailed help combines registry signature with doc-derived parameter descriptions;
     `Args` are consumed for operator help, while `Returns` is optional and not required for v1 operator contract;
   - `guards`: detailed help comes from explicit guard catalog entries;
   - `codecs`: detailed help comes from explicit codec metadata plus registry type mapping.
6. Metadata ownership and enforcement:
   - internal components must provide non-empty `summary` and non-empty detailed operator description;
   - for internal actions, "detailed description" means explicit workflow-node usage metadata, not class docstring;
   - v1 enforcement point is test/CI quality gates for internal components (not runtime hard-fail);
   - external components are best-effort; if metadata is missing, help output must state that the description
     is not provided by the external component.
7. JSON contract stability:
   - `help-components` JSON response includes top-level `contract_version` and `components`, where
     `components` contains normalized type keys (`actions`, `functions`, `validators`, `guards`, `codecs`);
   - `help-component` JSON response includes top-level `contract_version` and `component`;
   - the type-level `help-component` JSON response includes top-level `contract_version` and
     `component_type` carrying `type`, `description` and `components`, where each `components` entry
     reuses the list entry shape (`name`, `summary`, `source`);
   - detailed component object keeps stable key names: `name`, `type`, `summary`, `description`,
     `parameters`, `source`, `notes`;
   - `parameters` is an object keyed by parameter name; each entry carries `type` (a display string),
     `description`, and `required` (boolean); for actions the additional `action_parameters` object
     lists `required` and `optional` parameter names;
   - `returns` is optional and type-specific; v1 function/validator operator help does not require it;
   - additive extension is allowed only via new optional fields; existing key names and structural nesting are stable.
8. Scope:
   - report component metadata and usage contracts only;
   - do not perform runtime validation or workflow linting in this command.
9. Testing policy for this ADR:
   - operator-contract and e2e acceptance tests must use core registered components, not test-local extra
     registrations;
   - if a required component is missing, implement it in core registration surface rather than registering
     it only in tests.
10. Core component generality policy:
   - when replacing test-local helpers with core components, design the component API to be reusable and
     domain-neutral rather than scenario-specific;
   - each newly introduced core helper in this scope must be justified by at least two realistic workflow
     scenarios.
11. Help-contract module structure:
   - introduce a dedicated operator-help module that maps runtime registrations into workflow-authoring
     documentation payloads;
   - target structure:
     - `workflow_engine/help_contract/models.py`: canonical DTOs for list/detail payloads;
     - `workflow_engine/help_contract/adapters/`: per-type adapters (`actions`, `functions`, `validators`,
      `guards`, `codecs`) that normalize metadata into DTOs;
     - `workflow_engine/help_contract/builder.py`: orchestration that assembles full help payloads from
      registries and static catalogs;
     - `workflow_engine/help_contract/renderers.py`: text/json rendering from DTOs without business logic.
12. WorkflowNode-oriented detail schema:
   - action detail payload must include a node-authoring section suitable for future workflow-creation commands:
     `node_template`, `action_parameters.required`, `action_parameters.optional`, `transition_hints`,
     `examples`;
   - function/validator detail payload must expose call parameters as node-configuration keys and descriptions
     (signature + Args extraction), independent from Python implementation narrative.
13. CLI coupling boundary:
   - CLI commands must call the help-contract builder and only render/route its DTOs;
   - CLI layer must not inspect registries directly for help output formatting logic.

## Alternatives considered

### A. Keep generic `--help` text only
Pros: lowest effort.  
Cons: not enough for workflow authoring; no discoverability of dynamic registrations.

### B. Docstring-only metadata (summary and details from `__doc__`)
Pros: low implementation cost; no extra metadata field.
Cons: weak enforceability for short list output, inconsistent quality, and a domain mismatch for actions where
class docstrings usually describe implementation rather than node authoring usage.

### C. Central static metadata catalog
Pros: explicit and consistent metadata in one place.
Cons: high drift risk against runtime registrations and plugin loading, additional maintenance burden.

### D. Hybrid runtime contract (chosen)
Pros: reflects actual loaded components; keeps short metadata explicit at registration point; reuses docstrings
for function/validator parameter guidance; keeps action guidance explicitly workflow-oriented; automatable and
stable for tooling.  
Cost: registry metadata extension, metadata backfill for internal components, and CI contract checks.

### E. CLI-coupled direct introspection in command handlers
Pros: fewer modules, fastest initial coding.
Cons: mixes CLI concerns with contract-building logic, harder to reuse for future workflow-creation commands,
and fragile for test coverage of contract semantics.

## Consequences

- A guard catalog abstraction is required for operator-facing descriptions.
- Internal component metadata quality becomes release-relevant, with action help modeled as workflow authoring
  contract rather than implementation docs.
- External module registrations remain visible through the same interface, with explicit missing-metadata reporting.
- Acceptance tests for this ADR must avoid test-only component registrations to keep the contract aligned with
  production core surfaces.
- Existing core components require metadata backfill work before freeze.
- Promoting test-only helpers into core requires API design discipline and at least one additional realistic
  usage scenario to prove reusability.
- A dedicated help-contract module adds one extra layer now, but becomes the reusable foundation for future
  operator commands that generate workflow nodes and transitions.

## Related ADRs

- ADR 005 component loading and plugin registration model (Accepted).
- ADR 007 CLI contract and session lifecycle for v1 (Accepted).

## Implementation notes

Implementation branch: `feature/adr_009-operator-help-and-component-introspection-contract` (merged).

Minimum v1 implementation:
- list and detail commands for all component types via `help-components` and `help-component`;
- deterministic JSON response shape with stable key names and structural nesting;
- at least one test with external module registration visibility.
- metadata quality gate test for internal components:
  - non-empty `summary`;
  - non-empty detailed operator usage description;
  - for functions/validators: parameter names from signature covered in detailed description;
  - for actions: required/optional node parameters documented as workflow-authoring contract.
- replace test-local helper registrations used by operator/e2e acceptance tests with reusable core helpers,
  validated by at least two realistic workflow scenarios.

CLI wiring options:
1. Thin-command wiring (recommended for v1):
   - `help-components` and `help-component` call use-case functions that invoke the help-contract builder;
   - command handlers only parse args and render DTO output.
2. Shared service wiring:
   - bootstrap builds a reusable `HelpContractService` and injects it into CLI use-cases;
   - better for future command expansion, slightly larger refactor.
3. Inline command wiring:
   - command handlers build payloads directly from registries;
   - not recommended because it violates the CLI coupling boundary in this ADR.

Acceptance boundaries for moving ADR 009 to Accepted:
1. Architecture boundary:
   - help payload assembly exists in the dedicated help-contract module; CLI handlers do not own contract logic.
2. Contract boundary:
   - list/detail payloads satisfy stable key names and nesting defined in this ADR, including `contract_version`.
3. Documentation boundary:
   - all internal actions expose workflow-node authoring metadata (not implementation-only text);
   - internal functions/validators expose parameter documentation derived from signature + Args mapping.
4. Testing boundary:
   - contract tests validate payload shape and required metadata presence for internal components;
   - operator/e2e acceptance coverage uses core registrations only, without test-local helper registration.
5. Reusability boundary:
   - core helpers promoted from tests are proven by at least two realistic scenarios.

## Change log

- Initial draft opened from phase 1 architecture planning session.
- Refined decision with hybrid metadata ownership, explicit internal/external enforcement policy, stable JSON
  contract keys, and ADR-specific testing policy forbidding test-local component registration in operator/e2e
  acceptance coverage.
- Added a core-component generality policy for migrating test-local helpers into reusable production
  registrations, with required validation by at least two realistic scenarios.
- Status changed from `Draft` to `Implementing`; implementation branch assigned.
- Corrected the documentation domain model: action operator help must describe workflow-node usage contract,
  not class implementation docstrings; function/validator help keeps signature plus Args-oriented documentation.
- Added explicit help-contract module structure, WorkflowNode-oriented detail schema, CLI wiring options, and
  acceptance boundaries for ADR 009 freeze.
- Implementation-stage refinements agreed in architecture discussion: fixed the `parameters` entry schema
  (`type`, `description`, `required`), extended the guard catalog with the `reversed` modifier and the
  `validators` shorthand as explicit `kind` entries, and settled action metadata declaration at the
  registration point (`register_action(metadata=...)`).
- Closed the testing and reusability boundaries: the test-local `adr006_*` registrations were replaced by
  the core components `echo_value`, `init_deque_param`, `init_list_param` and `enqueue_folder_entries`,
  proven by two realistic scenarios (the recursive scan/resume e2e and a new recursive copy-tree e2e);
  `copy_file` additionally accepts an existing folder as `path_target`, copying into it under the source
  file name.
- Added the type-level `help-component` mode as an outcome of operator e2e review: `--component-name`
  became optional, and without it the command returns the type description with the list of its
  components under the new top-level `component_type` key. The `help-components` contract is unchanged
  and remains the automation surface.
- Status changed from `Implementing` to `Accepted`; the feature branch was merged into `development`
  and the ADR was frozen with the delivered contract.
