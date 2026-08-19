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

`examples/` ships two validated templates. Each declares its `inputs` and its deliverable, and runs
from any working directory the `workflow-engine` command is reachable from (see "Requirements").
Session data lands under `<cwd>/.workflow-engine/` unless the config file or `--work-dir` says
otherwise.

Both templates treat a missing deliverable as a failed run: the node that writes the CSV fails under
the error code it produced, so the run ends with exit code `3` and the code in `errors` instead of
reporting success with no file.

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

`--input NAME[:TYPE]=VALUE` is repeatable; `TYPE` names a registered codec. `help-components` lists
codecs under their Python module path (e.g. `pathlib._local.Path` for `Path` on this Python version);
the bare name shown above (`Path`) also resolves and is what the examples use. `set-input` only binds
to a session that has not started yet; `run --input` binds and starts in one call.

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
