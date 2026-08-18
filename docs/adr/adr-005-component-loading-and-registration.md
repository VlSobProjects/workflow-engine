# ADR 005: Component loading and plugin registration model

## Status
Accepted

## Active branch
—

## Context

The engine relies on decorator-based registries:

- `ACTION_REGISTRY` for actions,
- `FUNCTION_REGISTRY` for action functions,
- `VALIDATOR_REGISTRY` for guard validators,
- `CODEC_REGISTRY` for codecs.

Registration happens only as an import side effect. The current system has no bootstrap contract that guarantees those imports before workflow execution.

One of the main product goals is a stable core with extensibility through plugins:

- plugin development inside this repository, but outside `workflow_engine` internals;
- plugin development in a separate project that depends on an installed `workflow_engine` core.

Today this goal is not supported by an explicit architecture contract.

Current evidence:

- `docs/architecture/overview.md` states there is no discovery mechanism yet.
- Tests explicitly import modules to populate registries (`tests/test_registration.py`, `tests/test_engine.py`).
- `WorkflowSessions` does not execute an explicit component loading phase before calling the engine.

As a result, runtime behavior depends on import order and caller discipline.

## Decision

Introduce an explicit, deterministic component loading contract owned by bootstrap:

1. Keep current decorator-based registries as the runtime extension mechanism.
2. Add a dedicated bootstrap API that loads component modules before any workflow node construction.
3. Support two loading sources in this ADR scope:
   - **Core modules**: fixed manifest shipped with `workflow_engine`.
   - **External modules**: explicit `external_modules` list from `WorkflowEngineConfiguration`.
4. Keep loading deterministic at the boundary level:
   - load all core modules first,
   - load external modules only after core loading succeeds.
5. Fail fast with configuration errors when a declared module target cannot be imported or initialized.

This ADR does **not** include Python entry-point discovery. Entry points are deferred as a future extension.

## Alternatives considered

### A. Keep import side effects only, without bootstrap contract
Pros: zero implementation cost.
Cons: hidden runtime dependency on import order; fragile behavior for new callers; poor operability.

### B. Entry-point discovery now
Pros: natural packaging model for external plugins.
Cons: weaker operator control over what gets loaded; unresolved conflict policy for same-name registrations from different packages.

### C. Explicit manifest + explicit config modules (chosen)
Pros: deterministic startup, auditable loading surface, full operator control over loaded external modules.
Cons: requires configuration maintenance for external modules.

## Consequences

- Startup becomes deterministic and reproducible across CLI/tests/integrations.
- Loading surface is explicit and controlled by configuration.
- Missing imports become explicit configuration failures instead of late "not registered" errors.
- Existing callers must invoke bootstrap once per process/session entrypoint.
- Operational cost: maintain external module paths in configuration.
- External packages are still supported when installed and referenced explicitly in `external_modules`.

## Related ADRs

- ADR 004 session bootstrap and configuration snapshot (Accepted): defines bootstrap boundary where this loader belongs.
- ADR 003 persistence boundary and run workspace (Accepted): keeps persistence concerns separate from bootstrap concerns.
- ADR 002 node composition (Accepted): relies on stable action/guard creation by name.

## Implementation notes

Target runtime architecture:

- `workflow_engine.bootstrap.component_loader` is the orchestrator and is called from bootstrap
  before engine construction.
- `workflow_engine.bootstrap.plugin_manifest` loads built-in core modules.
- `workflow_engine.bootstrap.plugin_external_modules` loads external modules from configuration.
- `workflow_engine.bootstrap.module_loader` is the shared import/initialization helper and
  normalizes loading errors.

Suggested package layout:

- `src/workflow_engine/bootstrap/component_loader.py`
- `src/workflow_engine/bootstrap/plugin_manifest.py`
- `src/workflow_engine/bootstrap/plugin_external_modules.py`
- `src/workflow_engine/bootstrap/module_loader.py`
- `src/workflow_engine/bootstrap/__init__.py`

Responsibilities and contracts:

- `ComponentLoader` orchestrates loading sources in deterministic order and surfaces typed
  configuration failures.
- `ManifestPluginSource` loads built-in core modules.
- `plugin_external_modules` loads configured external module targets.
- `module_loader` imports modules (and optional `module:function` targets) and adds source/module
  context to configuration errors.
- Registries remain unchanged; loading only triggers module import so decorator registration runs.

`__init__.py` policy:

- Keep `__init__.py` files thin (package marker and optional exports).
- Do not rely on registration side effects from `__init__.py`.
- Plugin entry module should be explicit (for example, `plugin.py`) and import its action/function/
  validator/codec modules.

Practical defaults:

- Default built-in core modules are:
  - `workflow_engine.codecs.base_codecs`
  - `workflow_engine.validators.output_function_validators`
  - `workflow_engine.actions.base_functions`
  - `workflow_engine.actions.action_nodes`

Implementation steps:

1. Define bootstrap contract:
   - `ComponentLoader` interface with `load_all()` and typed configuration errors.
2. Add core module manifest.
3. Add external modules contract:
   - `external_modules` in configuration;
   - each item is `module` or `module:function`.
4. Implement loader orchestration:
   - load core modules first;
   - load external modules second;
   - collect and report loading failures with source and exception type.
5. Wire into bootstrap path so loading happens before engine usage.
6. Keep backward compatibility:
   - provide default core modules equal to current built-ins.
7. Add runtime guardrails:
   - optional strict mode that verifies registries are non-empty after bootstrap.
8. Publish plugin authoring guide for explicit module configuration.

Testing steps:

1. Positive local plugin test:
   - core modules + local external module load expected registry entries.
2. Positive external plugin test:
   - installed external package module path in config registers expected components.
3. Missing module test:
   - manifest includes one invalid module path and returns a configuration error.
4. Broken module target test:
   - `module:function` target not found and returns explicit configuration error with module and source.
5. Determinism test:
   - repeated bootstrap calls produce stable registry key sets.
6. Resume parity test:
   - new session and resumed session behave the same with the same loader configuration.
7. Regression test:
   - workflow using `function` action starts without manual `importlib.import_module(...)` in test setup.

Success criteria:

- Plugin registration works in both modes: built-in core modules and configured external modules.
- No test path needs ad hoc module imports only to populate registries.
- Workflow start/resume fails fast and explicitly when manifest is invalid.
- Workflow start/resume fails fast and explicitly when external module loading is invalid.
- Registry content for built-ins is stable across repeated runs.
- Existing example workflow executes successfully under bootstrap contract.

Test data for testing:

1. `manifest_valid_minimal`:
   - local modules:
     - `workflow_engine.codecs.base_codecs`
     - `workflow_engine.validators.output_function_validators`
     - `workflow_engine.actions.base_functions`
     - `workflow_engine.actions.action_nodes`
2. `manifest_with_local_plugin`:
   - valid minimal manifest + `tests.plugins.local_extra_actions`
3. `manifest_invalid_module`:
   - valid minimal manifest + `workflow_engine.actions.not_existing_module`
4. `external_module_valid`:
   - test package module path in config: `ext_sample.plugin`
5. `external_module_broken_target`:
   - config target points to missing `module:function`
6. `workflow_smoke_function_action`:
   - minimal workflow JSON using `function` action and one guarded transition.
7. `workflow_resume_same_manifest`:
   - one interactive node workflow to verify continue path after persisted state.

## Change log

- Initial draft created from architecture backlog cleanup session.
- Refined scope: primary goal is plugin extensibility with stable core, in both local-module and external-package models.
- Added concrete runtime architecture details: bootstrap package layout, `ComponentLoader` orchestration
  point in `engine.py`, `__init__.py` policy, built-in manifest defaults, and entry-point discovery flow.
- Aligned decision with implemented architecture: explicit core manifest + explicit `external_modules`
  configuration; deferred entry-point discovery to future work.
- Added constraint for future entry-point ADR: resolve registration conflict policy (including
  same-name components from different modules/packages) before implementation.
