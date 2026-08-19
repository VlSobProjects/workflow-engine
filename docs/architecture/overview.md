# Architecture overview

This document describes the architecture of the project as it currently is.

It is incomplete. Only the parts settled by an accepted decision are described. Open architectural
questions and ideas that are not yet decisions live in `docs/architecture/notes/`.

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
| Action | Performs the work and produces one `ActionNodeOutput`. An error is a value in that result; an exception that escapes the action reaches the engine, which ends the run as failed. |
| Transition | A guard and a static target. The first transition whose guard holds is taken. |

An action is either automatic, and the engine continues, or interactive, and the engine returns a
`PresentResponse` to its caller and stops until it is called again. The core interactive action is
`ask`; the exchange it takes part in is described under "Interactive exchange" below.

A target is one of:

- a node identifier, which is the only **routing** target,
- the end of the workflow,
- failure of the node, under a code.

If a node declares no routing target, the workflow ends after it. If it declares one and no guard
holds, the node fails. A transition whose target is the node itself, or one carrying `attempts`,
retries the node while the node's `max_attempts` (default `3`) still allows it. Once the allowance is
spent, a self-targeting transition fails the node under `max_attempts_exceeded`, and a transition that
carries `attempts` towards another node finally takes that route. A failure target's code is optional:
when the transition configuration omits `fail`, the node fails under the error code the action already
produced instead of a new one.

## Guards

A guard is the only predicate concept. Its `check` method receives the action result, a read-only
state view, and a trace list; it returns a boolean, appends its answer to the trace, and never writes
anything to the state. The name of a guard is the error code of a node that fails it through the
`validators` expansion. A node that declares a routing target and matches no transition fails under the
error code its action produced, or under `no_transition_matched` when the action produced none.

The state view exists so the engine can resolve `param.`, `output.`, and `artifact.` references in a
guard's configuration before it runs; the registered predicate function behind a function guard never
receives the state itself, only the values already resolved into it.

Kinds: comparison against a value, a registered function returning a boolean, a match on the error
code, the absence of an error, and the nested groups `all_of` and `any_of`. Any guard may be negated.

The configuration key `validators` is a short form for a post-condition. When a node is built, each
entry becomes a leading transition `all_of(no_error, not P)` targeting failure under the name of `P`.
The transitions built from it no longer reference `validators`, but the raw list stays on
`WorkflowNode.config` as part of the node's own definition.

## Interactive exchange (see ADR 013)

A node whose action is interactive asks a question and the run stops there. There is one contract
whoever answers: an operator, an agent, or a calling program. Who answered is data about the answer,
recorded in the journal, not a property of the node, so the engine needs no taxonomy of interactive
node types.

The core action is `ask`. Its node configuration carries the presentation (title, instruction,
options, hints and the rest, with `param.`/`output.`/`artifact.` references resolved as in any node)
and an `answer` declaration in the shape of the workflow `inputs` block, validated by the same
function. Beside it an `errors` catalogue names the failure codes the node accepts. Declaration and
catalogue travel together as the `AnswerContract` of the presentation; the engine reads them from the
built node and never from the concrete action class.

**Pausing.** The engine journals the engine event `workflow_paused_interactive` with the node id and
the declared names, saves the state, and returns. The paused position needs no state field of its
own: it is `state.current_node_id` plus the execution mode of the built node. The command reports a
paused workflow (exit code `2`) and carries a `question` block in `data` — the node id, the
presentation, the declared answer, the error catalogue and the generic code. That block, not
`PresentResponse`, is the caller-facing contract: the same class also carries setup errors, budget
stops, node failures and completion.

**Answering.** `resume` takes `--answer <json>` or `--answer-file <path>`. The document carries
`status` (`success` | `failure`), `values`, an optional `text`, `error_code` and `message` on failure,
and an optional `actor` label. A success becomes an `ActionNodeOutput` whose values are `SET` writes —
the only write mode an answer has — and whose `text` is the output text of the node, so value guards
route on it and `save_as` stores it. A failure becomes an output carrying its error code, which the
node's own transitions route like any other failure. Either way the answer goes through the node's
guards and transitions, never around them, and is journaled as the operator event
`interactive_answered` with the answered names and their codecs, never the values; the actor label
rides in the event details because `SessionEvent.actor` stays the two-valued engine/operator
distinction of ADR 006.

**Refusing.** An answer is accepted only when the current node's action is interactive and the last
session event is `workflow_paused_interactive`; otherwise it would be a fabricated node output.
Refused as well: a malformed document, an undeclared or missing required name, a value the declared
codec cannot decode, and an error code outside the node's catalogue. Every refusal exits `4`, applies
nothing and journals nothing — a refused command did not happen to the run.

**Asking again.** `resume` without an answer presents the same question again, consuming neither an
attempt nor a visit, which is all an escalation needs. A transition back to the node consumes an
attempt and is bounded by `max_attempts` like anywhere else. A question waiting for an answer is not
engine work, so the ADR 010 node budget does not bound how long it stays open.

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

`StateModel` carries everything a resumed run needs: session identity (`session_id`, `flow_id`,
`schema_version`, `timestamp`), the current node, the node visit/attempt counters and the
`max_nodes_visited`/`nodes_visited` soft-limit budget (see ADR 010), the output and error of each
node plus the latest `error_code`/`error_msg`, the guard results of the latest attempt of each node,
the parameters saved through `save_as`, and the working directory.

Values in parameters are serialized through codecs, so a parameter keeps its Python type across a
save and a load.

`state.params` is an engine-managed flat bus: actions return typed `param_writes`, and the engine
applies and persists them on each turn. Session-level control outcomes are stored in
`state.session_events` as a persisted append-only journal, and artifact-registration outcomes
(`artifact_overwritten`, `artifact_path_conflict`) are stored the same way in `state.artifact_events`.

### Artifacts and deliverables (see ADR 011)

`state.artifacts` holds registered artifacts as a map of logical name to `WorkflowArtifact`
(relative path, creation timestamp, description). Artifacts always live under `work_dir/artifacts`;
only relative paths are stored.

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
in status derivation so they never corrupt the session status. The terminal `run`/`resume` result
additionally carries `data.export` with the resolved `destination` and the exported map, so a caller
that asked for an export learns where the files went without reading the event journal; the key is
absent when no export ran.

`copy_artifact(source_artifact_name, target_artifact_name, state, target_path=None,
allow_overwrite=False)` copies and registers a new artifact from an existing one (copy-promote
pattern). Move/delete semantics are out of scope; the source artifact stays registered.

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
the session has not started; a started run rejects it. When an assignment names a type and the
declaration names one too, both must resolve to the same codec, otherwise the binding is rejected.
Starting a session with an unbound `required` input fails at setup with the missing names before any
node executes (exit code `4`), after journaling a `workflow_setup_failed` event that carries them. The
declared inputs surface in the `run`/`resume`/`show-state` result data next to `deliverables`.

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

`--work-dir`/`WE_WORK_DIR` and `--storage-dir`/`WE_STORAGE_DIR` resolve independently of each other's
config value: giving only `--storage-dir` does not read `work_dir` from the config file (the runtime
root falls back to the default), and giving only `--work-dir` (or `WE_WORK_DIR`) does not read
`storage.storage_dir` from the config file (storage falls back to `<work_dir>/json-storage/`) — an
explicit `--storage-dir` is required to use a storage location the config file names independently of
`work_dir`.

**Config discovery**, in order: the explicit `--config` path; `<cwd>/.workflow-engine/
workflow_engine_config.json`; `<user_config_dir>/.workflow-engine/workflow_engine_config.json`
(`platformdirs.user_config_dir()`); otherwise `<runtime_root>/workflow_engine_config.json`. Whichever
path is resolved, a file that is not there is created with the resolved defaults, and that includes an
explicit `--config` path that does not exist yet.

**Default paths**: when no explicit path is provided, the runtime root defaults to `<cwd>/.workflow-engine/`,
which holds sessions under `<work_dir>/sessions/<session_id>/`, storage under `<work_dir>/json-storage/`,
and config at the runtime root. Relative paths are resolved against the current working directory. Stored
paths remain in POSIX form regardless of OS (ADR 008).

### Public commands

- `init-new-session` to create a session without starting execution; accepts `--max-nodes-visited` to
  set its initial soft limit;
- `run` to create and execute a session; accepts repeatable `--input NAME[:TYPE]=VALUE` to bind
  declared inputs before execution (ADR 012);
- `resume` to continue an existing session; accepts `--answer <json>` or `--answer-file <path>`, which
  are mutually exclusive and both optional, to answer a node the run is paused at (ADR 013);
- `set-input` to bind typed values to declared workflow inputs of an unstarted session, one or more
  `--input NAME[:TYPE]=VALUE` per call (ADR 012);
- `set-limit` to update the per-session `max_nodes_visited` soft limit; it refuses any value below the
  current limit, and `0` is the one exception, disabling the soft limit while the run stays bounded by
  the global hard safety cap. The number of nodes already visited does not enter the rule;
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

The CLI is the only writer of standard output: the engine reports a failure through the response it
returns and the session event journal, never by printing, so `--json` output stays parseable on the
failure path. A failure that the state does not record as a node error, such as an exception escaping
an action, reaches the caller through the `errors` field of the response. That field carries only
what actually failed, so a caller may read a non-empty map as a failure and a completed run reports
none. The same holds for a malformed command line: the argument parser writes its message and the
usage to standard error, and under `--json` standard output still carries one command result with
`command_status: error`.

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
adds `execution_mode` and the node-authoring sections (`node_template`,
`action_parameters.required/optional`, `transition_hints`, `examples`), a guard detail adds `kind` and
a codec detail adds `python_type`; a type-level payload carries `component_type` with `type`,
`description` and `components` entries in the list shape (`name`, `summary`, `source`). Existing keys
and nesting are stable; extension is additive only.

`source` states where a component is defined, not which loading path registered it: the engine's own
package is `core` and every other module is `external`, so a component registered by a launcher
script is reported as external like one loaded through `external_modules`. A codec is addressed by
the rule of ADR 012, a full registered name or an unambiguous bare class name, the same rule the
input surface uses.

Metadata sources per type: actions and codecs declare explicit metadata at the registration point;
functions and validators combine the signature with `Annotated`/`Args` parameter documentation;
guard kinds are described by a static catalog keyed by the configuration keys an operator writes,
including the `reversed` modifier and the `validators` shorthand. Internal components must carry
complete metadata, enforced by a test quality gate; external registrations stay visible and report
missing metadata explicitly.

## Open questions

Open architectural questions and ideas that are not yet decisions are tracked in
`docs/architecture/notes/`, not here — the overview is the architecture as built.
