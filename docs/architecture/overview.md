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
so `param.` and `output.` in a guard configuration keep working.

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

Public commands are:

- `init-new-session` to create a session without starting execution;
- `run` to create and execute a session;
- `resume` to continue an existing session;
- `set-limit` to update the per-session `max_nodes_visited` soft limit;
- `show-state` to render persisted session state;
- `list-sessions` to list sessions discoverable under the configured `work_dir`;
- `help-components` to list registered components;
- `help-component` to show one component by type and name.

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

- Default runtime and storage path policy for CLI calls remains open. See ADR 008.
- The engine-wide hard safety cap for unbounded runs remains open. See ADR 010.
- The error and retry policy beyond the allowance a transition declares.
