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

Beside the two run-wide budgets a single node may declare its own ceiling, `max_visits` (see
ADR 017). The engine checks it when it is about to run the node, before the action, and fails the
workflow under `max_visits_exceeded` naming that node. There is no default: a node without the key is
bounded only by the budgets above. The two answer different questions — the budgets protect the host
from any definition, `max_visits` stops one loop at the node that causes it — and a business bound,
which is dynamic, belongs in the flow data instead: a parameter that guards and functions resolve.

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

`max_attempts` bounds one visit, and leaving the node resets it, so a loop that returns through
another node is not bounded by it. The optional `max_visits` bounds the visits themselves: the engine
refuses to enter the node once it has completed that many, and fails the workflow under
`max_visits_exceeded`. The check runs before the action, so the node has no output at that point and
its own transitions never see the code — the exhaustion is not routable, exactly as
`max_attempts_exceeded` is not. A declared `max_visits` below `1` is a configuration error.

## Guards

A guard is the only predicate concept. Its `check` method receives the action result, a read-only
state view, and a trace list; it returns a boolean, appends its answer to the trace, and never writes
anything to the state. The name of a guard is the error code of a node that fails it through the
`validators` expansion. A node that declares a routing target and matches no transition fails under the
error code its action produced, or under `no_transition_matched` when the action produced none.

The state view exists so the engine can resolve `param.`, `output.`, and `artifact.` references in a
guard's configuration before it runs; the registered predicate function behind a function guard never
receives the state itself, only the values already resolved into it.

**A guard sees the state as it was before its own node wrote to it.** The engine selects the
transition first and applies the node's `param_writes`, output text and artifacts afterwards, when the
step is taken. So a guard routing out of a node cannot read what that node just produced through the
bus — it reads the action result, which is what it is given. A loop that accumulates therefore puts
its exit check at the head of the loop, on a node that runs after the write has landed, rather than on
the node that performs the write.

Kinds: comparison against a value, a registered function returning a boolean, a match on the error
code, the absence of an error, and the nested groups `all_of` and `any_of`. Any guard may be negated.

The configuration key `validators` is a short form for a post-condition. When a node is built, each
entry becomes a leading transition `all_of(no_error, not P)` targeting failure under the name of `P`.
The transitions built from it no longer reference `validators`, but the raw list stays on
`WorkflowNode.config` as part of the node's own definition.

## Interactive exchange (see ADR 013, ADR 015)

A node whose action is interactive asks a question and the run stops there. There is one contract
whoever answers: an operator, an agent, or a calling program. Who answered is data about the answer,
recorded in the journal, not a property of the node, so the engine needs no taxonomy of interactive
node types.

The core action is `ask`. Its node configuration carries the presentation (title, instruction,
options, hints and the rest, every field of it template text) and an `answer` declaration in the
shape of the workflow `inputs` block, validated by the same function. Beside it an `errors` catalogue names the failure codes the node accepts. Declaration and
catalogue travel together as the `AnswerContract` of the presentation; the engine reads them from the
built node and never from the concrete action class.

**Template text.** A presentation field, and the authored file a template-rendering function
reads, resolve a `param.`/`output.`/`artifact.` reference both as a whole value, the way any node
configuration does, and inside their text through the braced `${param.name}` form, with `$$` for a
literal `$`. Templating is a property of the declared field and
of nothing else: the ADR 009 help surface marks which parameters are template text, and every other
configuration string keeps its exact meaning, so a literal `${` in a function parameter or a written
file is untouched. All ten presentation fields are in the set, because they already resolved
whole-value references through one function and because `description` defaults to the raw
`instruction`. The two failures sit at two times: a malformed template refuses the node when it is
built, among the per-node configuration errors of ADR 001, and an unresolved reference fails the run
where the presentation is built, in the error class whole-value resolution already raises. Neither is
routable — a presentation precedes any output of its node, so no guard could read it. Resolution is
engine resolution and runs no user code, which is what lets a plain `resume` re-present the same
question (ADR 016). Template text sourced from an authored file follows the same rules with one
difference of timing: the file is read when the node runs, so a malformed placeholder there is the
routable function error `template_malformed` rather than a build-time refusal (ADR 020).

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
distinction of ADR 006. The event also places the answer in the run, as the `visit` of the node and
the `attempt` ordinal within that visit: the counters are enforcement state and reset on departure,
so the journal is where a retry leaves a record that survives (see ADR 017).

**Computing on the answer.** An interactive action may carry a registered function, and `ask` does:
with `function_name` (plus optional `function_parameters`) the function runs on an accepted answer
before the answer becomes the output the node's guards see. What it returns is the node output, all
of it — output text, parameter writes, artifacts and error code — so a function that does not keep
the writes it was given drops the answered values. It runs between the state view and the transition
selection, which is why the state it reads is the state the guards read; a failure answer routes on
its declared code and never reaches it, and a failing function fails the node the way any registered
function does. The journal is unchanged: `interactive_answered` records what was supplied, and what
the function made of it is the node's output, journaled as any output is.

Two core functions are written for that injection and register in `actions/answer_functions`:
`echo_answer` surfaces a declared answer value into the output text, and `collect_answer` appends the
answer to a collection parameter and reports `enough` or `more` against a minimum. They are the
components of the stage rather than new mechanism: each replaces a node that existed only to adjust
data beside a question — the surfacing node in front of the guards, and the append-and-check pair at
the head and the tail of an accumulating loop. Both edit the output they are given, because a
function that builds a fresh one drops the answered values, and both fail the node under a code when
the value or the collection they were configured with is not there.

**Refusing.** An answer is accepted only when the current node's action is interactive and the last
session event is `workflow_paused_interactive`; otherwise it would be a fabricated node output.
Refused as well: a malformed document, an undeclared or missing required name, a value the declared
codec cannot decode, and an error code outside the node's catalogue. Every refusal exits `4`, applies
nothing and journals nothing — a refused command did not happen to the run.

**Asking again.** `resume` without an answer presents the same question again, consuming neither an
attempt nor a visit, which is all an escalation needs — and because it consumes no visit it can never
exhaust the node's `max_visits` either. A transition back to the node consumes an attempt and is
bounded by `max_attempts` like anywhere else; a correction routed through another node comes back as
a fresh visit, which is what `max_visits` bounds. A question waiting for an answer is not engine work,
so the ADR 010 node budget does not bound how long it stays open.

## Model call (see ADR 014)

A node whose action is `llm` calls a model and binds its reply, without pausing the run. It is the
automatic counterpart of `ask`: the two share the answer declaration and sit on opposite sides of one
boundary — `ask` binds an answer produced outside the engine, `llm` is a call the engine performs
itself and audits itself.

The node declares `provider`, the prompt as template text under the ADR 016 contract, and `answer`,
the typed declaration of ADR 013. Optional: `model`, overriding the provider's default as a literal
that resolves no reference; `format`, `text` (the default, binding the whole reply to at most one
declared name, a second refused at build time) or `json` (an object keyed by the declared names);
`options`, passed to the adapter unread; and `record`, opting into the audit artifacts.

The action resolves the prompt, calls the adapter, extracts the raw values according to `format`, and
decodes them through their codecs — the same decoding path as the ADR 013 answer binding, so the two
declarations cannot drift. The `param_writes` of the resulting output carry the values and the
`output_text` is the raw reply. Under `json` the reply is read as it stands, and where it is not JSON
the first JSON object it carries is taken: what surrounds or annotates the object is removed, its own
syntax is never repaired.

**Adapters.** A provider adapter is a registered class, not a callable, and the engine seats one
instance per configured provider name for the lifetime of a process. The seat is module state
(`providers/provider_seat.py`), reachable from a registered function shipped by an adapter package,
which the engine object would not be. The instance exists so an adapter speaking to a local model
server can remember which model is resident; that memory is a cache of a fact outside the process, so
an adapter works with an empty one and re-checks the server before acting on it.

The contract is two operations: the call — prompt, model, options and the provider settings in, reply
text or a classified failure out — and `finalize(reason)`, invoked on every seated adapter when a run
ends, with `completed`, `failed`, `paused`, `aborted` or `reconfigured`. The engine holds no policy
there. An adapter that fails to release is reported under a `provider:<name>` key in the `errors` of
the response and changes neither the outcome of the run nor its exit code.

The core ships one adapter, `fake` — the null implementation of the contract, scripted replies and no
network. The real adapters live in `src/workflow_engine_providers/`, an add-on package beside the
engine loaded through `external_modules` like any plugin: `openai_compatible`, which speaks that
protocol and nothing else, `lmstudio`, which subclasses it and adds model residency, and
`ollama_systemone`, a sibling over Ollama's decision endpoint: the prompt is the state, the typed
questions travel in the call options, and the reply text is a JSON object of question name to
probability or answer object, which the `llm` node binds like any `json` reply — the contract is
unchanged.

**Configuration.** The engine configuration file carries a `providers` section: per provider name,
`adapter`, `base_url`, `model`, `api_key_env` — the *name* of the environment variable holding the
credential, read at call time, never the credential — and `options` for what only the named adapter
understands. A key beside those five is a configuration error, as is a node naming an unconfigured
provider and a block naming an unregistered adapter; none of the three is routable. The section is
not snapshotted into `session.json`: it is the environment of a run rather than its identity, so a
moved session resolves the providers of the machine it runs on.

**Failure.** Every failure is a node error code. The adapter classifies its own into six —
`transient`, `rate_limited`, `permanent`, `invalid_request`, `timeout`, `context_overflow` — and the
action owns three more: `llm_answer_invalid` for a reply the declaration refused, `provider_failed`
for an adapter that raised instead of classifying, and `llm_record_failed` for an audit that could
not be written. `context_overflow` is a class of its own because the engine carries no tokenizer: the
provider's refusal is the only overflow signal there is, and a guard that sees it routes the run into
a branch that splits the data. Chunking is that graph pattern and never a hidden behaviour of the
action. There is no retry policy: the `max_attempts` self-loop allowance is the whole of it.

**Audit.** The account of a call rides on the `details` of the action output into the record of the
visit (see "Node records"): the provider, the model the adapter reported, the model requested, the
status, the error class where it failed, and the token counts the adapter reported. Records are never
read back during a run, so a node of the same run reaches the facts of a call only through the bus:
where the `llm` node names a parameter in `save_call_as`, the action writes the same facts there as a
dictionary of fixed keys, an unknown fact as null, on every way out of the node — the writes of a node
are applied whether it failed or not, so the node a failure transition leads to reads them too. The
parameter holds the last call; the records hold every call. Where the node sets `record: true`, the prompt
and the reply are written as artifacts named `<node_id>.prompt.<visit>.<attempt>` and
`<node_id>.reply.<visit>.<attempt>` under `artifacts/llm/`, the same two ordinals the record carries.
A failed call leaves its prompt and no reply.

## Registries

Components are registered at import time by decorators and looked up by name from a configuration.

| Registry | Holds | Populated by |
| --- | --- | --- |
| `ACTION_REGISTRY` | Action classes by `action_type` | `@register_action` |
| `FUNCTION_REGISTRY` | Functions returning `ActionNodeOutput` | `@register_function` |
| `VALIDATOR_REGISTRY` | Functions returning `bool`, used by guards | `@register_validator` |
| `CODECS` and `CODEC_REGISTRY` | Codecs by Python type and by type name | `@register_type` |
| `PROVIDER_REGISTRY` | Provider adapter classes by adapter name | `@register_provider` |

A module that registers something has to be imported by bootstrap before workflow execution.
`ComponentLoader` loads built-in core modules first and then configured external modules.

Beside its own resolved `function_parameters`, a registered function is given what its caller injects,
and the two conventions differ on purpose: an action's function receives `state`, the read-only view,
and `output`, the `ActionNodeOutput` the node received — the previous node's output, or the accepted
answer at an interactive node — while a guard's validator receives the output *text* as `output` and
the object as `action_output`, and never the state. Both live in `function_injection`, so a caller
adds a call rather than a copy.

Guards and transitions are not registries: their classes are listed in their own modules.

## State

`StateModel` carries everything a resumed run needs: session identity (`session_id`, `flow_id`,
`schema_version`, `timestamp`), the current node, the node visit/attempt counters — enforcement state
owned by the engine, which is why a node cannot write them — and the
`max_nodes_visited`/`nodes_visited` soft-limit budget (see ADR 010), the output and error of each
node plus the latest `error_code`/`error_msg`, the guard results of the latest attempt of each node,
the parameters saved through `save_as`, and the working directory.

Values in parameters are serialized through codecs, so a parameter keeps its Python type across a
save and a load.

`state.params` is an engine-managed flat bus: actions return typed `param_writes`, and the engine
applies and persists them on each turn. Session-level control outcomes are stored in
`state.session_events` as a persisted append-only journal, and artifact-registration outcomes
(`artifact_overwritten`, `artifact_path_conflict`) are stored the same way in `state.artifact_events`.

What each node visit did is not in the state at all. The per-node slots hold the latest visit and the
next one overwrites them, so the history of a loop lives in the node-record stream beside the state
file (see "Node records").

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

Composing what an artifact holds is the work of registered functions, not of a document model
(ADR 020): `dict_list_to_pretty_table` writes one table, `dict_list_to_grouped_tables` writes a
table per group under its heading, `write_text_artifact` writes a text value as it stands, and
`render_template_to_artifact` renders an authored template file against the state. A template
substitutes references and never iterates, so a shape that needs iteration is a function.
The template path is absolute or relative to the workflow definition file, whose directory the
state records when the session is created.

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
declared inputs surface in the `run`/`resume` result data next to `deliverables`; they left the
`show-state` result with ADR 018, and until a workflow-definition introspection surface exists the
definition itself is the reference for what a run must have bound.

## Storage

`Storage` is an abstract class over a state source, a workflow source and a node-record source.
`JsonStorage` is its only implementation and keeps them under `<storage_dir>/<session_id>/` as
`state.json`, `workflow.json` and `records.jsonl`. The state is written on every turn.

The record stream is append-only and lives outside the state on purpose: the state holds what a
resume needs, the trail holds what an explanation needs (ADR 021). The contract carries two
operations for it — append one record, and read records filtered by node and bounded by a tail — and
the engine only ever writes to it during a run.

Storage is built per session, not once per process, because a session decides which storage it uses.

The state file is replaced, never rewritten in place: the new content is written to a temporary file
in the same directory, flushed to disk and then renamed onto `state.json`. A run interrupted while
writing therefore leaves the previous state readable and the session resumable, which is what makes
the per-turn write safe to rely on. A rename refused with a permission error — on Windows, another
program holding `state.json` open for an instant — is attempted again a few times over about a
second and a half before the save fails, and a save that fails names the class and the message of
its cause beside the path. The workflow definition and the session record are written once
when the session is created, and the record stream is only ever appended to one line at a time, so
neither needs the same treatment.

## Node records

Every node visit leaves one record, written by the engine and by nothing else. See ADR 021.

A record describes a visit that concluded: the engine appends it after the output was applied and
the transition was chosen, so a record only ever names effects that took hold. A visit paused at a
question has concluded nothing and is recorded when its answer concludes it; an entry refused by
`max_visits` is recorded as the visit the node was not allowed to make.

| Member | What it holds |
| --- | --- |
| `record_id`, `timestamp` | Identity and order, the `SessionEvent` discipline |
| `node_id`, `visit`, `attempt` | Where and which time, the ordinals the answered event uses |
| `action`, `function` | The registered action, and the function where the action wraps one |
| `status`, `error_code` | `completed` or `failed`, with the code when there is one |
| `guards`, `transition` | The guards the visit was asked, and where it went: a node, the end, a failure |
| `writes`, `artifacts` | The parameters the visit applied by name, codec and write mode, and the artifacts it registered |
| `details` | The open member the engine fills per action kind |

`details` is filled by the action rather than by the engine, which copies it and reads nothing in it.
Only `llm` fills it today, with the account of its call (see "Model call").

A record carries names and codec names and never a value: the ADR 013 §9 journal rule holds for the
trail unchanged. Values live in the state and in artifacts, and a payload that must survive — the
prompt and the reply of a model call — is written as an artifact the record then names.

The engine never reads the stream back during a run. It exists for the reader who explains a
finished, failed or abandoned run from the session directory alone, through `show-records`.

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

### One writer per session

The engine is a single writer per session. Two processes running the same session would each read the
state, act on it and write it back, and the second write would drop what the first one did without
either of them noticing. Every call that writes the state — creating a session, starting or continuing
a run, binding inputs, setting a limit — therefore holds the session for the duration of the call.

The hold is a `session.lock` file in the session directory, created in one step that either succeeds or
reports that the file is already there. It carries the holder's process id and the moment it was taken,
so a refusal can name who holds the session. A second writer is refused as an engine error and reaches
the caller as a setup error; it never waits and never overwrites.

Reading a session takes nothing: `show-state`, `list-parameters`, `show-parameter`, `show-journal`,
`show-records` and `export-artifact` answer while a run holds the session.

A lock is not expired by age. A node waiting on a slow model call holds its session legitimately for
minutes, and a hold taken away from a live run protects nothing. A lock left behind by a process that
died is therefore removed by the operator, and the refusal names the file to remove.

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

The same rule holds wherever the engine turns a state value into text, not only where it stores one:
`render_value_as_text` renders a path with `as_posix()`, and the surfaces that render go through
it — a value guard comparing against a resolved reference, the functions that surface a value into an
output text (`echo_value` from the state, `echo_answer` from an accepted answer), and the
presentation of an interactive node. Without it a `Path` parameter would compare and print with native
separators on Windows while the same value is persisted and serialized as POSIX, so a guard could fail
against the very path the previous node had just written. The same function renders a list or a dict
as compact JSON, written with `common_encoder`, the encoder the state serialization uses: a collection
therefore reaches a guard, an output text or a published question in the form the state itself is
written in, rather than as the Python repr `str()` would produce (ADR 016).

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
- `show-state` to render the state of a run (see "Session read surfaces");
- `list-parameters` to name the parameters of a session, and `show-parameter` to read one value;
- `show-journal` to read the session event journal, optionally bounded by `--tail` and filtered by
  `--node`;
- `show-records` to read the node records of a session, one per concluded node visit, bounded and
  filtered the same way;
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

## Session read surfaces

Five commands read a session, one shape of result each, and none of them moves the run. See ADR 018
and, for the last of them, ADR 021.

`show-state` is the state of the run and nothing else: the envelope, the timestamp, `flow_id`,
`schema_version`, `work_dir`, `current_node`, the visit counters and budget, the error fields, the
artifacts in the three ADR 011 spellings, `deliverables`, and `guard_results` — the guard answers of
the latest attempt per node. Artifacts, deliverables and guard traces stay because each is bounded by
the workflow's declaration or by construction, while `parameters`, `outputs` and `inputs` grew with
the run and left the result.

`list-parameters` answers with `{name, type, source_node}` per parameter, the codec name and the
writing node, never a value. `show-parameter --name` answers with one: the ADR 016 rendering as plain
text, and under `--json` the codec envelope the state persists (`object`, `object_type`) beside the
name and the writing node, so a machine reader keeps the type and can feed the value into `set-input`
of another session. A name that is not set is a resolution error, `command_status: error` and exit
code `4`, the answer `help-component` gives for an unregistered component.

`show-journal` publishes `session_events` as persisted — timestamp, code, actor, event id and
details. The whole journal by default, because asking for it is an explicit act; `--node` filters to
the events that name a node and `--tail` then keeps the last `n` of them, and the answer reports its
own size next to the size of the whole journal. A non-positive `--tail` is a command error rather
than an empty answer. The journal holds names, codec names and ordinals and never values (ADR 013
§9), so no read surface can publish the values of an exchange.

`show-records` publishes the node-record stream as persisted, in the same discipline: the whole
stream by default, `--node` filtering to one node and `--tail` keeping the last `n` of what is left,
the answer reporting its own size next to the size of the whole stream, and a non-positive `--tail`
a command error. It answers a different question from `show-journal` — the journal says who drove the
session, the records say what the run did — and the two are never bookkept twice.

All five are info commands: they report `workflow_status` and `event_code` informationally, exit `0`
on command success wherever the workflow stands, and `4` on a session or a name that does not
resolve.

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
type keys `actions`, `functions`, `validators`, `guards`, `codecs`, `providers`; a detail payload keeps the stable
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
