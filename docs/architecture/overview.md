# Architecture overview

This document describes the architecture of the project as it currently is.

It is incomplete. Only the parts settled by an accepted decision are described. The decisions that
are still open are listed at the end.

Scope rules for this document:
- Describe structure, components and their relations.
- Do not repeat the rationale, alternatives or trade-offs; those belong to the ADRs.
- Update it in the same merge that changes the architecture.

## Shape of a run

A workflow is a graph of nodes described in JSON. The engine walks it one node at a time and returns
to its caller whenever a node needs something from outside.

```
caller -> engine -> node: action -> transitions -> node ...
                     |                    |
                   state <----------------+
```

`WorkflowEngine.start_workflow` is the entry point. It loads the state and the definition from a storage, builds every
node from the definition, checks that every transition target exists, and then runs until the
workflow ends, a node fails, or a node needs an exchange with the caller.

Every run is bounded by two node budgets (see ADR 010): the per-session `max_nodes_visited` soft
limit, operator-controlled via `set-limit` with `0` meaning no soft limit, and the global
`hard_max_nodes_visited` safety cap from the engine configuration (default `1000`). Reaching the
soft limit pauses the run with `workflow_paused_limit`; reaching the hard cap pauses it with
`workflow_paused_safety_limit`. The hard cap cannot be changed by a session command: continuing past
it requires raising the value in the configuration file before the resume.

## A node

A node is **one action and an ordered list of guarded transitions**. See ADR 002.

| Part | Contract |
| --- | --- |
| Action | Performs the work and produces one `ActionNodeOutput`. An error is a value in that result. |
| Transition | A guard and a static target. The first transition whose guard holds is taken. |

An action is either automatic, and the engine continues, or interactive, and the engine returns a
`PresentResponse` to its caller and stops until it is called again with a result.

A target is one of:

- a node identifier, which is the only **routing** target,
- the end of the workflow,
- failure of the node, under a code.

If a node declares no routing target, the workflow ends after it. If it declares one and no guard
holds, the node fails. A transition whose target is the node itself, or one carrying `attempts`,
retries the node within the allowance of `max_attempts`.

## Guards

A guard is the only predicate concept. It receives the whole action result, returns a boolean, and
exposes a name identifying the rule. It never receives the state and never writes anything: the
caller passes a list of records and each guard appends its answer, which the engine then stores under
the node. The name of a guard is the error code of a node that fails it.

Guards read the state only through the parameter references the engine resolves before calling them,
so `param.`, `output.`, and `artifact.` in a guard configuration keep working.

Kinds: comparison against a value, a registered function returning a boolean, a match on the error
code, the absence of an error, and the nested groups `all_of` and `any_of`. Any guard may be negated.

The configuration key `validators` is a short form for a post-condition. When a node is built, each
entry becomes a leading transition `all_of(no_error, not P)` targeting failure under the name of `P`.
Nothing of it survives into the runtime node.

## Registries

Components are registered at import time by decorators and looked up by name from a configuration.

| Registry | Holds | Populated by |
| --- | --- | --- |
| `ACTION_REGISTRY` | Action classes by `action_type` | `@register_action` |
| `FUNCTION_REGISTRY` | Functions returning `ActionNodeOutput` | `@register_function` |
| `VALIDATOR_REGISTRY` | Functions returning `bool`, used by guards | `@register_validator` |
| `CODECS` and `CODEC_REGISTRY` | Codecs by Python type and by type name | `@register_type` |

A module that registers something has to be imported by bootstrap before workflow execution.
`ComponentLoader` loads built-in core modules first and then configured external modules.

Guards and transitions are not registries: their classes are listed in their own modules.

## State

`StateModel` carries everything a resumed run needs: the current node, counters of visits and
attempts, the output and error of each node, the guard results of the latest attempt of each node,
the parameters saved through `save_as`, and the working directory.

Values in parameters are serialized through codecs, so a parameter keeps its Python type across a
save and a load.

`state.params` is an engine-managed flat bus: actions return typed `param_writes`, and the engine
applies and persists them on each turn. Session-level control outcomes are stored in
`state.session_events` as a persisted append-only journal.

### Artifacts and deliverables (see ADR 011)

`state.artifacts` holds registered artifacts as a map of logical name to `WorkflowArtifact`
(relative path, description). Artifacts always live under `work_dir/artifacts`; only relative paths
are stored.

A workflow definition may declare an optional `deliverables` block: an ordered list of logical
artifact names that constitute the product of the workflow. Validated at build time for shape only;
the named artifacts may not exist until runtime.

Nodes address artifacts through engine-resolved `artifact.<logical_name>` references, which return
the absolute POSIX path of the registered artifact at execution time. An unregistered name is the
node contract error `artifact_not_found`, caught at the action level and returned as a node error
value.

On `workflow_completed`, when an export destination is known (`--export-dir` CLI option or
`export_dir` config, highest wins), the engine copies each declared deliverable to that directory.
Export is non-fatal: missing or unwritable deliverables record session events
(`deliverable_missing`, `artifact_export_failed`) but do not change the completed status.
Successful export records an `artifacts_exported` event. All three event codes map to `COMPLETED`
in status derivation so they never corrupt the session status.

`copy_artifact(source, target, target_path, allow_overwrite)` copies and registers a new artifact
from an existing one (copy-promote pattern). Move/delete semantics are out of scope; the source
artifact stays registered.

### Input parameters (see ADR 012)

A workflow definition may declare an optional `inputs` block — the input-side mirror of
`deliverables`: an ordered list of declarations, each with a `name`, an optional codec `type`, a
`required` flag (default true) and an optional description. Validated at build time for shape only
(unique names matching `[A-Za-z_][A-Za-z0-9_]*`; a declared `type` must name a registered codec).

An operator binds typed values before the first node runs, either with `set-input` on a prepared
session or the one-shot `run --input`. Each `--input NAME[:TYPE]=VALUE` is decoded through the codec
(JSON-parsed with a raw-string fallback for typed values; an untyped value stays a literal string)
and written to `state.params` as a `SET` write through the normal path, journaled as an `inputs_set`
operator event that records the bound names and codecs, not the values. Binding is allowed only while
the session has not started; a started run rejects it. Starting a session with an unbound `required`
input fails at setup with the missing names before any node executes (exit code `4`). The declared
inputs surface in the `run`/`resume`/`show-state` result data next to `deliverables`.

## Storage

`Storage` is an abstract class over a state source and a workflow source. `JsonStorage` is its only
implementation and keeps both under `<storage_dir>/<session_id>/` as `state.json` and `workflow.json`.
The state is written on every turn.

Storage is built per session, not once per process, because a session decides which storage it uses.

## Sessions

A session owns a directory under `<work_dir>/sessions/<session_id>/`, which is the `work_dir` of the run.
Next to the run files it holds `session.json`, the session record. See ADR 004.

| Field | Meaning |
| --- | --- |
| `session_id` | Identifier of the session and the name of its directory |
| `work_dir` | The session directory itself |
| `flow_id`, `schema_version` | The workflow the session was started from |
| `storage` | The storage settings the session was created with |
| `timestamp` | When the session was created |

The record is written once, when the session is created, and is never rewritten.

Global configuration supplies storage settings only when a **new** session is created. A resumed session
reads its record first and builds storage from it, so changing the global storage settings later does not
affect sessions that already exist.

Loading a session validates the record before the state is read: the record must be readable, must sit in
the directory it describes, and must carry the requested `session_id`. Anything else fails as an engine
error. The engine additionally checks that the record and the loaded state agree.

`work_dir` is the discovery root. A session is found only while the configuration points at the `work_dir`
it was created under; discovery across several `work_dir` roots is not part of the current architecture.

Paths are serialized in POSIX form, so a record or a state written from one shell reads back identically
from another.

## CLI

The public CLI entry point is the installed `workflow-engine` console script. It uses a thin `argparse`
transport layer and dispatches into command use cases.

### Path resolution (see ADR 008)

The runtime root, work directory, storage directory, and config file use deterministic defaults with
explicit precedence rules. See ADR 008 for the full policy.

**Precedence** (highest to lowest):
1. Explicit CLI options: `--work-dir`, `--storage-dir`, `--config`
2. Environment variables: `WE_WORK_DIR`, `WE_STORAGE_DIR`
3. Config file values (if found)
4. Defaults: `<cwd>/.workflow-engine/`

**Default paths**: when no explicit path is provided, the runtime root defaults to `<cwd>/.workflow-engine/`,
which holds sessions under `<work_dir>/sessions/<session_id>/`, storage under `<storage_dir>/`, and config
at the runtime root. Relative paths are resolved against the current working directory. Stored paths
remain in POSIX form regardless of OS (ADR 008).

### Public commands

- `init-new-session` to create a session without starting execution;
- `run` to create and execute a session; accepts repeatable `--input NAME[:TYPE]=VALUE` to bind
  declared inputs before execution (ADR 012);
- `resume` to continue an existing session;
- `set-input` to bind typed values to declared workflow inputs of an unstarted session, one or more
  `--input NAME[:TYPE]=VALUE` per call (ADR 012);
- `set-limit` to update the per-session `max_nodes_visited` soft limit (`0` disables it, but the
  run stays bounded by the global hard safety cap);
- `show-state` to render persisted session state;
- `list-sessions` to list sessions discoverable under the configured `work_dir`;
- `help-components` to list registered components;
- `help-component` to show one component by type and name;
- `export-artifact` to copy one named artifact or all declared deliverables of a session to a
  target directory (works for completed, paused and failed sessions).

Command results are normalized as `command`, `session_id`, `command_status`, `workflow_status`,
`event_code`, `message`, `errors`, and `data`. Text output is for operators, JSON output is for
automation. Exit codes are `0` for successful completion and non-runner commands, `2` for paused
workflow commands, `3` for failed workflow commands, and `4` for command-level setup or resolution
errors.

## Operator help contract

`help-components` and `help-component` expose the registered components as an operator contract.
See ADR 009.

The payloads are assembled in the `help_contract` module: `models.py` holds the DTOs, `adapters/`
normalizes each component type, `builder.py` assembles payloads from the registries and the static
guard catalog, and `renderers.py` renders DTOs as text or JSON. The CLI commands consume the builder
only and never inspect registries themselves.

`help-component` has two modes: with `--component-name` it renders the detail card of one component;
with only `--component-type` it renders the type-level view, the description of the component type
and the list of its components. `help-components` is the full-list automation surface.

JSON payloads carry a top-level `contract_version`. The list groups components under the normalized
type keys `actions`, `functions`, `validators`, `guards`, `codecs`; a detail payload keeps the stable
keys `name`, `type`, `summary`, `description`, `parameters`, `source`, `notes`, and an action detail
adds the node-authoring sections (`node_template`, `action_parameters.required/optional`,
`transition_hints`, `examples`); a type-level payload carries `component_type` with `type`,
`description` and `components` entries in the list shape (`name`, `summary`, `source`). Existing keys and nesting are stable; extension is additive only.

Metadata sources per type: actions and codecs declare explicit metadata at the registration point;
functions and validators combine the signature with `Annotated`/`Args` parameter documentation;
guard kinds are described by a static catalog keyed by the configuration keys an operator writes,
including the `reversed` modifier and the `validators` shorthand. Internal components must carry
complete metadata, enforced by a test quality gate; external registrations stay visible and report
missing metadata explicitly.

## What is not settled yet

- The error and retry policy beyond the allowance a transition declares.
