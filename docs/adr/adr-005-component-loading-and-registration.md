# ADR 005: Component loading and plugin registration model

## Status
Draft

## Active branch
None

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
- `WorkflowSession` does not execute an explicit component loading phase before calling the engine.

As a result, runtime behavior depends on import order and caller discipline.

## Decision

Introduce an explicit, deterministic plugin loading contract owned by session bootstrap:

1. Keep current decorator-based registries as the runtime extension mechanism.
2. Add a dedicated bootstrap API that loads plugin modules before any workflow node construction.
3. Support two extension channels:
   - **Local modules**: explicit manifest of module import paths.
   - **External packages**: Python entry points in group `workflow_engine.plugins`.
4. Keep loading deterministic:
   - load local manifest modules first (declared order),
   - then load entry-point plugins in stable sorted order by entry-point name.
5. Fail fast with configuration errors when a declared module or entry-point target cannot be imported.

Plugin authors only need to provide importable modules that register actions/functions/validators/codecs through existing decorators.

## Alternatives considered

### A. Keep import side effects only, without bootstrap contract
Pros: zero implementation cost.
Cons: hidden runtime dependency on import order; fragile behavior for new callers; poor operability.

### B. Entry-point discovery only
Pros: natural packaging model for external plugins.
Cons: weaker local development ergonomics, less explicit control in deployments that require strict loading surface.

### C. Hybrid: explicit local manifest + entry-point plugins (chosen)
Pros: simple local extension path and first-class external plugin path; deterministic startup; auditable loading surface.
Cons: moderate implementation cost; requires both manifest maintenance and entry-point contract documentation.

## Consequences

- Startup becomes deterministic and reproducible across CLI/tests/integrations.
- Plugin development is supported both in-project and in separate installed projects.
- Missing imports/entry points become explicit configuration failures instead of late "not registered" errors.
- Existing callers must invoke bootstrap once per process/session entrypoint.
- Operational cost: maintain a local manifest and document entry-point conventions.

## Related ADRs

- ADR 004 session bootstrap and configuration snapshot (Draft): defines bootstrap boundary where this loader belongs.
- ADR 003 persistence boundary and run workspace (Accepted): keeps persistence concerns separate from bootstrap concerns.
- ADR 002 node composition (Accepted): relies on stable action/guard creation by name.

## Implementation notes

Target runtime architecture:

- `workflow_engine.bootstrap.component_loader` is the orchestrator and is called from `engine.py`
  before any node construction (`workflow_node_factory`) and before the execution loop.
- `workflow_engine.bootstrap.plugin_manifest` loads ordered local modules (built-ins and local plugins).
- `workflow_engine.bootstrap.plugin_entrypoints` discovers and loads external plugins from Python
  entry points.

Suggested package layout:

- `src/workflow_engine/bootstrap/component_loader.py`
- `src/workflow_engine/bootstrap/plugin_manifest.py`
- `src/workflow_engine/bootstrap/plugin_entrypoints.py`
- `src/workflow_engine/bootstrap/__init__.py`

Responsibilities and contracts:

- `ComponentLoader` orchestrates loading sources in deterministic order and surfaces typed
  configuration failures.
- `ManifestPluginSource` imports module paths from manifest in declared order.
- `EntryPointPluginSource` discovers entry points from group `workflow_engine.plugins`,
  sorts by entry-point name, and loads each target.
- Registries remain unchanged; loading only triggers module import so decorator registration runs.

`__init__.py` policy:

- Keep `__init__.py` files thin (package marker and optional exports).
- Do not rely on registration side effects from `__init__.py`.
- Plugin entry module should be explicit (for example, `plugin.py`) and import its action/function/
  validator/codec modules.

Practical defaults:

- Default built-in local modules are exactly the modules currently imported in tests:
  - `workflow_engine.codecs.base_codecs`
  - `workflow_engine.validators.output_function_validators`
  - `workflow_engine.actions.base_functions`
  - `workflow_engine.actions.action_nodes`

External plugin discovery model:

- External package declares entry point in its `pyproject.toml`:
  - `[project.entry-points."workflow_engine.plugins"]`
  - `my_plugin = "my_wfe_plugin.plugin"`
- Loader uses `importlib.metadata.entry_points(group="workflow_engine.plugins")`.
- Entry points are processed in stable sorted order by `name`.
- Each `ep.load()` imports plugin target module; decorators in that module register components.

Implementation steps:

1. Define bootstrap contract:
   - `ComponentLoader` interface with `load_all()` and typed configuration errors.
2. Add local module manifest model:
   - `components.local_modules` (ordered list of module import paths).
3. Add external plugin contract:
   - entry-point group `workflow_engine.plugins`;
   - each entry point resolves to a plugin module import target.
4. Implement hybrid loader:
   - import local modules in declared order;
   - load entry-point plugins in stable sorted order;
   - collect and report module/entry-point import failures with source and exception type.
5. Wire into session start/resume:
   - call loader from `engine.py` before `workflow_node_factory` usage and before engine loop start.
6. Keep backward compatibility:
   - provide default local manifest equal to current built-in modules.
7. Add runtime guardrails:
   - optional strict mode that verifies registries are non-empty after bootstrap.
8. Publish plugin authoring guide:
   - minimal plugin layout for local module and external package;
   - entry-point declaration examples.

Testing steps:

1. Positive local plugin test:
   - local manifest with built-in and local plugin modules loads expected registry entries.
2. Positive external plugin test:
   - installed test package exposes `workflow_engine.plugins` entry point and registers expected components.
3. Missing module test:
   - manifest includes one invalid module path and returns a configuration error.
4. Broken entry-point test:
   - entry point target import fails and returns explicit configuration error with plugin name.
5. Determinism test:
   - repeated bootstrap calls produce stable registry key sets.
6. Resume parity test:
   - new session and resumed session behave the same with the same loader configuration.
7. Regression test:
   - workflow using `function` action starts without manual `importlib.import_module(...)` in test setup.

Success criteria:

- Plugin registration works in both modes: local manifest and installed external package.
- No test path needs ad hoc module imports only to populate registries.
- Workflow start/resume fails fast and explicitly when manifest is invalid.
- Workflow start/resume fails fast and explicitly when entry-point plugin loading is invalid.
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
4. `entrypoint_plugin_valid`:
   - test package entry point: `workflow_engine.plugins = ext_sample = ext_sample.plugin`
5. `entrypoint_plugin_broken`:
   - test package entry point points to missing target module
6. `workflow_smoke_function_action`:
   - minimal workflow JSON using `function` action and one guarded transition.
7. `workflow_resume_same_manifest`:
   - one interactive node workflow to verify continue path after persisted state.

## Change log

- Initial draft created from architecture backlog cleanup session.
- Refined scope: primary goal is plugin extensibility with stable core, in both local-module and external-package models.
- Added concrete runtime architecture details: bootstrap package layout, `ComponentLoader` orchestration
  point in `engine.py`, `__init__.py` policy, built-in manifest defaults, and entry-point discovery flow.
