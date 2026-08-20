# workflow-engine

A small engine that executes workflows described in JSON.

A workflow is a graph of nodes. Each node runs one action, and an ordered list of guarded
transitions decides where the workflow goes next. The state of a run is persisted, so a workflow can
be resumed.

## Layout

| Path | Contents |
| --- | --- |
| `src/workflow_engine/` | The engine |
| `tests/` | Tests |
| `examples/` | Example workflow definitions |
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

`work_dir` and `storage.storage_dir` are also overridable per call with `--work-dir`/`--storage-dir`
or the `WE_WORK_DIR`/`WE_STORAGE_DIR` environment variables, which win over the config file. Full
precedence and path resolution: `docs/architecture/overview.md`.

On Windows without long-path support, keep the runtime root short. Artifacts live several levels below
`work_dir`, so a deep runtime root pushes them past the 260-character limit and the run fails while
writing the deliverable, with `pretty_table_write_error` and an `[Errno 2]` message.

## Running the examples

`examples/` ships three validated templates. Each declares its `inputs`, and runs from any working
directory the `workflow-engine` command is reachable from (see "Requirements"). Session data lands
under `<cwd>/.workflow-engine/` unless the config file or `--work-dir` says otherwise.

The two batch templates treat a missing deliverable as a failed run: the node that writes the CSV
fails under the error code it produced, so the run ends with exit code `3` and the code in `errors`
instead of reporting success with no file. The third template stops mid-run and waits for an answer.

### folder-inventory-to-csv

Walks a folder tree and writes a CSV inventory (path, size, MIME type, modified time, MD5) as the
`file_scan_table` deliverable. Requires the input `scan_root` (`Path`). A tree that holds no file at
all produces no table: the run fails with the error code `pretty_table_no_data`.

Step by step:

```
workflow-engine init-new-session --workflow-file examples/folder-inventory-to-csv.json --json
workflow-engine set-input --session-id <SESSION_ID> --input "scan_root:Path=<folder-to-scan>"
workflow-engine resume --session-id <SESSION_ID> --json
```

Or in one shot:

```
workflow-engine run --workflow-file examples/folder-inventory-to-csv.json \
  --input "scan_root:Path=<folder-to-scan>" --json
```

### flatten-copy-tree

Walks a folder tree and copies every file into a flat target directory, writing a copy report
(source, copied path, MD5) as the `copy_report` deliverable. Requires `source_root` and `target_dir`
(both `Path`); **`target_dir` must already exist.** If it does not, the first copy fails the
`COPY_FILE` node with the error code `target_folder_not_found`, the run stops as a failed workflow
(exit code `3`) with that code under `errors.COPY_FILE`, and no file is copied; create the directory
and start again. A file that cannot be copied fails the run the same way, under `copy_failed`.

```
workflow-engine run --workflow-file examples/flatten-copy-tree.json \
  --input "source_root:Path=<folder-to-copy>" --input "target_dir:Path=<destination-folder>" --json
```

### approve-and-copy

Asks for a decision before it copies anything, which is what an `ask` node is for: the run stops, the
command reports a paused workflow (exit code `2`), and nothing else happens until someone answers.
Requires `source_file` and `target_dir`; **`target_dir` must already exist.**

```
workflow-engine run --workflow-file examples/approve-and-copy.json \
  --input "source_file:Path=<file-to-copy>" --input "target_dir:Path=<destination-folder>" --json
```

The paused result carries the question under `data.question`: the node, the text of the question, the
declared answer, and the error codes the node accepts. Every presentation field is template text, so
the file and the size the previous node measured stand inside the instruction the answerer reads
rather than beside it.

```json
"question": {
  "node_id": "ASK_APPROVAL",
  "title": "Approve the copy",
  "instruction": "Decide whether '<file-to-copy>' (1.20 KB) may be copied. Answer 'approved' or 'rejected' as the answer text, and name the decision maker in 'reviewer'.",
  "options": ["approved", "rejected"],
  "answer": [{"name": "reviewer", "type": null, "required": true, "description": "Who made the decision"}],
  "error_catalogue": {"source_unreadable": "The file cannot be read, so no decision can be made."},
  "generic_error_code": "answer_failed"
}
```

Answer it with `resume --answer` (or `--answer-file <path>` for the same document in a file):

```
workflow-engine resume --session-id <SESSION_ID> --json \
  --answer "{\"status\": \"success\", \"values\": {\"reviewer\": \"me\"}, \"text\": \"approved\"}"
```

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
on. In this template an answer text that is neither `approved` nor `rejected` sends the run back to
the same node, which is bounded by its `max_attempts` (`2` here) and then fails under
`max_attempts_exceeded`. That bound covers one visit only: leaving the node resets it, so a
correction routed through another node comes back as a fresh visit and starts the attempts over. A
node that a loop can re-enter that way is bounded by the optional `max_visits` — see "Bounding a loop
through one node".

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

`--input NAME[:TYPE]=VALUE` is repeatable; `TYPE` names a registered codec. `help-components` lists
codecs under their Python module path (e.g. `pathlib._local.Path` for `Path` on this Python version);
the bare name shown above (`Path`) also resolves and is what the examples use. `set-input` only binds
to a session that has not started yet; `run --input` binds and starts in one call.

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

`show-state --session-id <SESSION_ID>` renders the full persisted state: `parameters`, `outputs`,
`artifacts_absolute`, `deliverables` and `inputs`.

Exit codes: `0` success, `2` workflow paused, `3` workflow failed, `4` command-level setup or
resolution error. A malformed command line is a `4` too: the message and the usage go to stderr, and
with `--json` stdout still carries one command result with `"command_status": "error"`, so a caller
that parses stdout never gets usage text instead of a document. Full CLI and artifact contracts:
`docs/architecture/overview.md`.

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
