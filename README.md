# workflow-engine

A small engine that executes workflows described in JSON.

A workflow is a graph of nodes. Each node runs one action, and an ordered list of guarded
transitions decides where the workflow goes next. The state of a run is persisted, so a workflow can
be resumed.

Why the engine exists — the challenges it answers and where it applies — is argued in
[`docs/motivation.md`](docs/motivation.md).

## Layout

| Path | Contents |
| --- | --- |
| `src/workflow_engine/` | The engine |
| `tests/` | Tests |
| `examples/` | Example workflow definitions and a walkthrough for each |
| `docs/` | Rules, architecture, ADRs and session notes |

## Requirements

Python 3.13 or newer. Dependencies are declared in `pyproject.toml`.

Every command below calls `workflow-engine`, the console script the package installs. Inside a clone
of this repository, run `uv sync` once and prefix the commands with `uv run`. From any other working
directory the script has to be reachable: either point uv at the project with
`uv run --project <path-to-repo> workflow-engine ...`, or install the package into an environment that
is on your `PATH`. A bare `uv run workflow-engine` outside the repository reports `program not found`.

## Configuration file

Every command reads a JSON config file, so the options you'd otherwise repeat on every call
(`--work-dir`, `--storage-dir`, `--export-dir`) can be set once instead. Search order, first match
wins:
1. `--config <path>`, if given.
2. `<cwd>/.workflow-engine/workflow_engine_config.json`, if it exists.
3. the OS user config directory (`platformdirs.user_config_dir()`, e.g. `%LOCALAPPDATA%` on Windows,
   `~/.config` on Linux) under `.workflow-engine/workflow_engine_config.json`, if it exists — a place
   for settings shared across every project on the machine.
4. none of the above exists: the engine creates one with resolved defaults at the runtime root
   (`<cwd>/.workflow-engine/` unless `--work-dir`/`WE_WORK_DIR` says otherwise) and uses it.

Whichever path is resolved, a file that is not there yet is created with the resolved defaults. That
includes an explicit `--config <path>` pointing at a file that does not exist: it is written where you
pointed it, not at the runtime root.

So the first command run in a fresh directory writes a starter config there, ready to edit:

| Key | Meaning | Default |
| --- | --- | --- |
| `work_dir` | Runtime root; sessions live under `<work_dir>/sessions/<session_id>/` | `<cwd>/.workflow-engine` |
| `storage.storage_dir` | Where session state and workflow files are kept | `<work_dir>/json-storage` |
| `export_dir` | Destination deliverables are copied to on workflow completion; `--export-dir` on `run`/`resume` overrides it per call, and if neither is set nothing is exported | `null` |
| `hard_max_nodes_visited` | Global safety cap on nodes visited per run/resume; config-only, no CLI flag (see "Hitting the hard node cap") | `1000` |
| `external_modules` | Extra Python module names imported at bootstrap to register plugin components (see "Writing a custom function") | `[]` |
| `providers` | The model providers an `llm` node may name: per provider name, the adapter that answers for it, its endpoint, its default model and the *name* of the environment variable holding the credential (see "Calling a model") | `{}` |

`work_dir` and `storage.storage_dir` are also overridable per call with `--work-dir`/`--storage-dir`
or the `WE_WORK_DIR`/`WE_STORAGE_DIR` environment variables, which win over the config file. Full
precedence and path resolution: `docs/architecture/overview.md`.

On Windows without long-path support, keep the runtime root short. Artifacts live several levels below
`work_dir`, so a deep runtime root pushes them past the 260-character limit and the run fails while
writing the deliverable, with `pretty_table_write_error` and an `[Errno 2]` message.

## Running the examples

`examples/` ships four validated templates, each with its own walkthrough:

| Template | What it does | Waits for an answer |
| --- | --- | --- |
| [`folder-inventory-to-csv`](examples/folder-inventory-to-csv.md) | Walks a folder tree and writes what it finds twice: a flat CSV inventory and a report holding one table per folder | no |
| [`flatten-copy-tree`](examples/flatten-copy-tree.md) | Copies every file of a tree into one flat directory and reports what it copied | no |
| [`approve-and-copy`](examples/approve-and-copy.md) | Asks for a decision, and copies the file only if the answer approves it | yes |
| [`reorganize-folder`](examples/reorganize-folder.md) | Audits a folder tree — hashes, duplicate groups, a category per file — and delivers a reorganization plan as prose and as a moves dictionary | no |

`folder-inventory-to-csv` ships in three named variants beside its base definition — `described`,
`tiered` and `chunked` — in which a model writes what each file contains, proposes what to do with
the inventory, and reads a file too large for it part by part. They need a provider configured (see
"Calling a model"), and the "Variants" section of the
[walkthrough](examples/folder-inventory-to-csv.md) covers all three.

What holds for all of them is in [`examples/README.md`](examples/README.md). What follows here is the
engine's own contract rather than any template's: how inputs are bound, how a question is answered,
how a model is called, how the result is retrieved, and how a session is read.

## Binding inputs

`--input NAME[:TYPE]=VALUE` is repeatable; `TYPE` names a registered codec. `help-components` lists
codecs under their Python module path (e.g. `pathlib._local.Path` for `Path` on this Python version);
the bare name (`Path`) also resolves and is what the examples use. `set-input` only binds to a
session that has not started yet; `run --input` binds and starts in one call.

### Writing a path on Windows

A `Path` input accepts native separators — `--input "src:Path=C:\data\in.txt"` binds the same value as
`C:/data/in.txt` — because the codec builds a `pathlib.Path`, which normalizes them. From there the
engine works in POSIX form everywhere: in `state.json`, in the JSON result, in a node output and in a
guard comparison. **Forward slashes are still the safer form to write**, for two reasons:

- A typed value is parsed as JSON before the codec sees it, with a fall back to the raw string. A bare
  `C:\data\in.txt` is not valid JSON, so it falls back and arrives intact — but a value that carries
  its own quotes (`--input 'src:Path="C:\data\in.txt"'`) *is* valid JSON, and there `\d` is rejected
  while `\t` and `\f` are a tab and a form feed. The path then binds silently as something else. Do
  not quote the value inside the assignment; the shell's own quotes around the whole `NAME=VALUE` are
  fine. The same holds for a path inside a JSON answer, where a backslash must be written `\\`.
- `pathlib` normalizes as it parses: `.\reports\out` binds as `reports/out`. The path still resolves
  the same way, but the form you get back is not the form you wrote.

## Answering an interactive workflow

A run that reaches an `ask` node stops and waits: the command reports a paused workflow (exit code
`2`) and carries the question under `data.question` — the node, the text of the question, the
declared answer, and the error codes the node accepts. Nothing else happens until someone answers.
[`approve-and-copy`](examples/approve-and-copy.md) shows a real one.

Answer it with `resume --answer <json>`, or `--answer-file <path>` for the same document in a file.

The answer document has one required field, `status`:

| Field | Meaning |
| --- | --- |
| `status` | `success` or `failure`. |
| `values` | The declared answer names and their values. Each is decoded by the codec its declaration names and written to the state. A `failure` carries none. |
| `text` | The output text of the node, which the transition guards compare. Defaults to `""`. |
| `error_code` | Required on `failure`: a code from `error_catalogue`, or the generic `answer_failed`. |
| `message` | Free text explaining a failure. |
| `actor` | Who answered, e.g. `operator` or `agent:reviewer-bot`. Recorded in the session journal. Defaults to `unspecified`. |

Anything else is refused with exit code `4` and changes nothing: an undeclared or missing name, a
value the codec cannot decode, an undeclared error code, a malformed document, or an answer sent to a
run that is not waiting for one. `resume` **without** an answer presents the same question again,
consuming neither an attempt nor a visit — that is how a caller who cannot answer hands the question
on.

An answer the node's transitions do not accept can be routed back to the same question, and the
node's `max_attempts` bounds that: when the attempts run out the node fails under
`max_attempts_exceeded`. The bound covers one visit only — leaving the node resets it, so a
correction routed through another node comes back as a fresh visit and starts the attempts over. A
node that a loop can re-enter that way is bounded by the optional `max_visits` — see "Bounding a
loop through one node".

Every field of the question is template text: `${param.<name>}`, `${output.<node_id>}` and
`${artifact.<logical_name>}` are replaced by the value they name when the question is presented, so
a value stands inside the sentence instead of beside it — `"Copy ${param.source_file} to
${param.target_dir}?"`. `$$` writes a literal `$`, and a field whose whole value is a bare
reference (`"context": "param.source_file"`) keeps working as before. A `$` that begins neither of
those refuses the node when the workflow is loaded, reported with the other node configuration
errors before anything runs; a reference that names nothing fails the run at the question instead
of reaching the answerer as written. A list or a dict is written into the text as compact JSON, a
path in POSIX form.

An `ask` node may also carry `function_name` and `function_parameters`, the same keys a `function` or
a `stop` node carries. The registered function then runs on an accepted answer, before that answer
becomes the output of the node: it is given the answer as its injected `output` argument, and what it
returns *is* the node output — the text the guards compare, the values written to the state, the
artifacts it registered, and the error code that fails the node. A failure answer routes on its own
code and never reaches the function. This is how one node routes on a declared answer value, keeps
every answer of a loop, or normalizes a reply that is nearly right, instead of a second node doing it;
`help-component --component-type actions --component-name ask` prints the keys and what the function
receives.

Two core functions take that injected answer, and a flow needs no code of its own to use the stage:
`echo_answer` puts a declared answer value into the output text, so the question that asked routes on
what it bound; `collect_answer` appends the answer to a list parameter prepared by `init_list_param`
and answers `enough` or `more`, so the question that asks accumulates its own answers and decides
when the loop is over. Both keep the writes the answer carried, and both fail the node under a code
rather than routing a value that is not there.

## Calling a model

An `llm` node is the automatic counterpart of `ask`: the engine performs the call itself, inside the
run, and the run does not pause. The node names a configured provider, carries the prompt as template
text, and declares what the reply must yield in the same shape as an `ask` answer and a workflow
`inputs` block:

```json
{
  "id": "CLASSIFY_FILE",
  "action_type": "llm",
  "action_parameters": {
    "provider": "local",
    "prompt": "Classify the file ${param.cur_path}. Answer with a JSON object holding \"category\" and \"confidence\".",
    "answer": [
      {"name": "category"},
      {"name": "confidence", "type": "float", "required": false}
    ],
    "format": "json",
    "options": {"temperature": 0},
    "record": true
  },
  "max_attempts": 3,
  "transitions": [
    {"guard": {"no_error": true}, "next": "NEXT_FILE"},
    {"errors": ["transient", "rate_limited"], "next": "CLASSIFY_FILE", "attempts": true},
    {"errors": ["context_overflow"], "next": "SPLIT_FILE"},
    {"fail": "classification_unavailable"}
  ]
}
```

The prompt is template text under the same rules as the fields of a question: `${param.<name>}`,
`${output.<node_id>}` and `${artifact.<logical_name>}` are replaced when the node runs, `$$` writes a
literal `$`, and substitution is single-pass, so a value full of `$` needs no escaping and cannot
smuggle a reference in. The values the reply carries are decoded through their codecs onto the bus,
and the raw reply is the output text of the node, which value guards compare.

`format` says how the reply is read. `text` (the default) binds the whole reply to the one declared
name; a second name is refused when the workflow is loaded. `json` reads an object whose keys are
the declared names, and takes the first JSON object the reply carries when the model wraps it in a
code fence, surrounds it with prose or annotates a member with a comment — what surrounds or
annotates the object is removed, the object's own syntax is never repaired. A reply the declaration
refuses is the routable node error `llm_answer_invalid`, with the raw reply still the output text.

`options` travels to the adapter unread by the engine: temperature, token limits, and anything else
the named adapter understands, including an instruction about its own resources such as releasing
the model after the call. `help-component --component-type providers --component-name <adapter>`
lists the options one adapter acts on.

### Configuring a provider

A node names a provider, never an endpoint and never a vendor. The name is resolved in the
`providers` section of the configuration file, so the same definition runs against a laptop and
against a hosted vendor without being edited:

```json
"external_modules": ["workflow_engine_providers"],
"providers": {
  "local": {
    "adapter": "openai_compatible",
    "base_url": "http://127.0.0.1:1234/v1",
    "model": "a-publisher/a-small-model",
    "options": {"timeout": 300}
  },
  "hosted": {
    "adapter": "openai_compatible",
    "base_url": "https://api.example-vendor.com/v1",
    "model": "the-vendor-model-id",
    "api_key_env": "EXAMPLE_VENDOR_API_KEY",
    "options": {"timeout": 60}
  }
}
```

| Key | Meaning |
| --- | --- |
| `adapter` | Which registered adapter answers for this name. Required |
| `base_url` | The endpoint root the adapter hangs its paths off |
| `model` | The model a node that names none is answered by |
| `api_key_env` | The **name** of the environment variable holding the credential, read at the moment of the call. Never the credential itself |
| `options` | What only the named adapter understands — a request timeout, what a model is loaded with — passed through unread |

A key beside those five is refused when the configuration is read rather than ignored, so a typo is
found at load and not at the first model call. A node naming a provider the installation does not
configure, and a block naming an adapter no loaded module registered, are configuration errors too:
wrong before the run, not during it, and therefore not routable.

Three adapters exist. `fake` ships in the core: it answers scripted replies without leaving the
process, which is what the test suite and the shipped examples run on. The other two are in
`workflow_engine_providers`, an add-on package beside the engine that is loaded the way any plugin
is loaded, by naming it in `external_modules` — `openai_compatible` speaks the OpenAI-compatible
chat protocol and reaches a local server and a hosted vendor alike, and `lmstudio` speaks the same
protocol and additionally loads and unloads models on an LM Studio server, releasing only what the
run loaded itself. `src/workflow_engine_providers/example_config.json` carries a filled-in example
of all of it, and `help-component --component-type providers` lists what the installation has.

An adapter that holds a resource is told when the run ends and decides for itself what to release.
If releasing fails, the failure is reported under a `provider:<name>` key in the `errors` of the
result and changes neither the outcome of the run nor its exit code: a model left resident on a
server is an operator's problem, not a failed workflow.

### When the call fails

Every failure is a node error code a transition can route, so a retry, a smaller chunk or a
different branch stays a decision of the graph. The adapter classifies its own failures into six:

| Class | What it says |
| --- | --- |
| `transient` | A hiccup; the same call may work again |
| `rate_limited` | The provider is throttling |
| `timeout` | No answer within the time the call allowed |
| `permanent` | The provider refuses and will keep refusing |
| `invalid_request` | The request itself is wrong |
| `context_overflow` | The provider refused the prompt as too large |

Three more belong to the action rather than to any provider: `llm_answer_invalid` for a reply the
answer declaration refused, `provider_failed` for an adapter that raised instead of classifying its
failure, and `llm_record_failed` for a call that was answered but whose audit files could not be
written.

`context_overflow` is a class of its own because the engine carries no tokenizer: the provider's
refusal is the only honest overflow signal there is, and a guard that sees it routes the run into a
branch that splits the data and calls the model per part. The `chunked` variant of
[`folder-inventory-to-csv`](examples/folder-inventory-to-csv.md) is that branch, built and measured.
There is no retry policy yet: a self-targeting transition bounded by the node's `max_attempts` is
the whole of it.

### What a call leaves behind

Every `llm` visit is accounted for in the node record of that visit, in its `details`: the provider,
the model that actually answered, the status of the call, the error class where it failed, and the
token counts the adapter reported.

```
workflow-engine show-records --session-id <SESSION_ID> --node DESCRIBE
```

```
... DESCRIBE visit 2 attempt 1  llm  completed  -> node COLLECT  guards: no_error=pass  writes: file_description (builtins.str, SET)  artifacts: DESCRIBE.prompt.2.1, DESCRIBE.reply.2.1  details: {"model":"a-publisher/a-small-model","provider":"local","status":"answered","usage":{"prompt_tokens":181,"completion_tokens":17}}
```

The record stream is where this has to live: the state keeps one slot per node and the next visit
overwrites it, so in a chunking branch or a retry loop only the records can say which model answered
which call.

The prompt and the reply themselves are artifacts, written when the node sets `record: true`, named
after the node and numbered by the same visit and attempt the record carries
(`<node_id>.prompt.<visit>.<attempt>`, `<node_id>.reply.<visit>.<attempt>`), so the files of one
call and its record are found by the same two numbers. They can be inspected after the run or
declared deliverables like any other artifact. A failed call leaves its prompt and no reply.

The provider block is deliberately not part of the session record: it is the environment a run
executes in rather than the identity of the run, so a session moved to another machine resolves the
providers of the machine it runs on. What actually answered is in the records instead, per call.

## Retrieving the result

A completed `run`/`resume` reports the declared deliverables and every registered artifact by
absolute path in its `data`. By default the file stays where the engine wrote it, inside the
session's own sandbox — nothing is copied anywhere on completion unless you ask for it:

```json
"deliverables": ["file_scan_table"],
"artifacts": {
  "file_scan_table": {
    "path": ".../sessions/<SESSION_ID>/artifacts/reports/file_scan_table.csv",
    "description": "Pretty table text from parameter: table_rows"
  }
}
```

Three ways to get the file itself:
- Read the absolute `path` directly from that output — it points inside the session sandbox, not
  into the directory you ran the command from.
- Pass `--export-dir <dir>` to `run` or `resume` (or set `export_dir` once in the config file — see
  "Configuration file"): on completion the engine copies every declared deliverable into `<dir>`,
  preserving its relative artifact path. The result reports where they went:

  ```json
  "export": {
    "destination": "<dir>",
    "exported": {"file_scan_table": "<dir>/reports/file_scan_table.csv"}
  }
  ```

  The key is present only when that export ran: a destination was resolved, the workflow declares
  `deliverables`, and the run completed.
- Run `export-artifact --session-id <SESSION_ID> --target-dir <dir> --all` (or `--artifact-name
  <name>` for one artifact) after the fact. Works for completed, paused and failed sessions.

## Reading a session

Four commands read a session, each with one shape of result. All four are info commands: they report
where the workflow stands in `workflow_status` without taking its exit code, so they answer `0` on
command success and `4` on an unresolvable session or name.

- `show-state --session-id <SESSION_ID>` is the state of the run and nothing else: status, last
  event, errors, current node, the visit counters and budget, the guard answers of the latest attempt
  per node in `guard_results`, and what there is to fetch — `deliverables`, `artifacts`,
  `artifacts_absolute` and `artifacts_path`. It carries no `parameters`, no `outputs` and no `inputs`;
  those grow with the run and have their own doors below.
- `list-parameters --session-id <SESSION_ID>` names what the run accumulated — `name`, the codec
  `type` and the `source_node` that wrote it — and never a value.
- `show-parameter --session-id <SESSION_ID> --name <NAME>` returns one value: the plain output is the
  rendered value, and `--json` carries the codec envelope exactly as the state keeps it, so the value
  feeds `set-input` of another session unchanged. An unknown name is an error, not an empty answer.

  ```json
  "data": {
    "name": "reviewer",
    "source_node": "ASK_APPROVAL",
    "value": {"object": "ops", "object_type": "builtins.str"}
  }
  ```

  `object_type` is the registered codec name, the same one `help-component --component-type codecs`
  lists and `--input NAME:TYPE=VALUE` accepts.
- `show-journal --session-id <SESSION_ID>` prints the session event journal — timestamp, code, actor,
  event id and details. The whole journal by default; `--tail <n>` keeps the last `n` events and
  `--node <NODE_ID>` keeps the events that name a node, and the two compose. The journal records
  names, codec names and ordinals, never the values themselves.
- `show-records --session-id <SESSION_ID>` prints what the run did, one line per concluded node
  visit — the node with its visit and attempt ordinals, the action and the function it ran, the
  status with its error code, the guards that were asked, the transition that was taken, and the
  parameters and artifacts the visit wrote. `--tail <n>` and `--node <NODE_ID>` bound and filter it
  the same way. This is where the history of a loop survives: the state keeps one slot per node and
  the next visit overwrites it. Like the journal, a record names a value and never carries it.

Exit codes: `0` success, `2` workflow paused, `3` workflow failed, `4` command-level setup or
resolution error. A malformed command line is a `4` too: the message and the usage go to stderr, and
with `--json` stdout still carries one command result with `"command_status": "error"`, so a caller
that parses stdout never gets usage text instead of a document. Full CLI and artifact contracts:
`docs/architecture/overview.md`.

## One process per session

A session is run by one process at a time. A command that writes the session — `run`, `resume`,
`set-input`, `set-limit` — holds it for the duration of the call, and a second one asking for the same
session is refused with exit code `4` and a message naming the process that holds it:

```
Session 6f1c... is held by process 4812 since 2026-08-25T09:14:03+00:00. If that process is gone,
remove the lock file to release the session: <work_dir>/sessions/<SESSION_ID>/session.lock
```

The hold is that `session.lock` file in the session directory. Reading a session never waits: the five
read commands and `export-artifact` answer while a run is in progress.

The lock does not expire, because a node waiting on a slow model call holds its session legitimately
for minutes. If a process was killed and left the file behind, delete it — nothing else uses it.

The state file itself is replaced rather than rewritten, so a run interrupted mid-write leaves the
previous state readable and the session resumable.

## Hitting the hard node cap

A recursive scan over a large tree can pause with `event_code: "workflow_paused_safety_limit"` (exit
code `2`) well before a short task flow would, because the hard node cap
(`docs/architecture/overview.md`, "Shape of a run") is one global number. Recovery: raise
`hard_max_nodes_visited` in the config file (see "Configuration file") and `resume` the session — the
run continues from where it paused. The cap's long-term scope (host vs. workflow vs. workflow class)
is open, tracked in
[`docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md`](docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md).

## Bounding a loop through one node

A node may declare `max_visits`, a whole number beside `max_attempts`:

```json
{ "id": "ASK_ROOT", "action_type": "ask", "action_parameters": {}, "max_visits": 3 }
```

The engine refuses to enter the node once it has completed that many visits and fails the run with
`"error_code": "max_visits_exceeded"` (exit code `3`), naming the node. The check happens before the
action, so a question beyond the cap is never published and never paid for, and the node's own
transitions cannot route the exhaustion — it is a failure of the workflow, like
`max_attempts_exceeded`.

There is no default: a node without the key is bounded only by the run-wide node caps above, which
stop the run at whatever node the budget ran out on rather than at the loop that ate it. Declare
`max_visits` as a seatbelt, an order beyond the passes the flow expects — a loop designed for up to
ten follow-ups declares, say, thirty. How many passes a task actually needs is flow logic, not a
safety cap: keep that number in the flow data, as a parameter that a guard or a function compares
against, so a run can decide "enough" from its own context.

## Writing a custom function

A `function`/`functions` action node calls a Python function registered with `@register_function`.
The same import-time decorator mechanism registers every kind of pluggable component (see
`docs/architecture/overview.md`, "Registries"): `@register_action`
(`workflow_engine.registry.action_registry`) for actions, `@register_validator`
(`workflow_engine.registry.function_registry`) for guard validators, and `@register_type`
(`workflow_engine.registry.type_registry`) for codecs. Everything below — the launcher-script path,
`external_modules`, and the importability requirement — applies the same way to all four; a function
is the concrete example.

Two ways to make one available, both verified against a real run:

### Fastest: register it in your own launcher script

Registration is a decorator side effect that runs the moment Python imports the function's module.
Define the function and call the CLI in the same process, before any config change:

```python
# run_it.py
from typing import Annotated
from workflow_engine.output import ActionNodeOutput
from workflow_engine.registry.function_registry import register_function


@register_function(summary="Shout a string in upper case.")
def shout(text: Annotated[str, "Text to upper-case"]) -> ActionNodeOutput:
    return ActionNodeOutput(output_text=text.upper())


from workflow_engine.cli.main import main
import sys

main(sys.argv[1:])
```

Run it as `python run_it.py run --workflow-file my_flow.json --json` instead of `workflow-engine
run ...`. No `external_modules` entry needed: the function is already in the registry by the time
the workflow starts.

### To use the plain `workflow-engine` command: `external_modules`

List the module by its importable name in the config file's `external_modules` (see "Configuration
file"):

```json
"external_modules": ["my_functions"]
```

The engine imports it with `importlib.import_module`, Python's standard mechanism — a script merely
sitting next to where you run `workflow-engine` from is **not** found on its own. Make the module
importable, either:
- `PYTHONPATH=<folder-containing-my_functions.py> workflow-engine run ...`, or
- turn the folder into an installed package (`uv pip install -e .`) for anything more than a quick
  one-off script.

### Function contract

- One `@register_function`-decorated function per registration; the decorator takes an optional
  `summary` string.
- Every parameter needs an `Annotated[<type>, "<description>"]` hint; the description surfaces in
  `help-component`.
- The function must declare `ActionNodeOutput` as its return type and return one.
- `help-component --component-type functions --component-name <name>` shows the registered
  contract, including whether it loaded from a core or an external module.

## Running the tests

Run tests from the repository root:

```
uv run pytest
```

## Working on this project

Read `AGENTS.md` for the entry point into the project rules, and `docs/README.md` for the
documentation map.
