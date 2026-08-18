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

So the first command run in a fresh directory writes a starter config there, ready to edit:

| Key | Meaning | Default |
| --- | --- | --- |
| `work_dir` | Runtime root; sessions live under `<work_dir>/sessions/<session_id>/` | `<cwd>/.workflow-engine` |
| `storage.storage_dir` | Where session state and workflow files are kept | `<work_dir>/json-storage` |
| `export_dir` | Destination deliverables are copied to on workflow completion; `--export-dir` on `run`/`resume` overrides it per call, and if neither is set nothing is exported | `null` |
| `hard_max_nodes_visited` | Global safety cap on nodes visited per run/resume; config-only, no CLI flag (see "Hitting the hard node cap") | `1000` |
| `external_modules` | Extra Python module names imported at bootstrap to register plugin components | `[]` |

`work_dir` and `storage.storage_dir` are also overridable per call with `--work-dir`/`--storage-dir`
or the `WE_WORK_DIR`/`WE_STORAGE_DIR` environment variables, which win over the config file. Full
precedence and path resolution: `docs/architecture/overview.md`.

## Running the examples

`examples/` ships two validated templates. Each declares its `inputs` and its deliverable, and runs
from any working directory with `uv run workflow-engine ...`. Session data lands under
`<cwd>/.workflow-engine/` unless the config file or `--work-dir` says otherwise.

### folder-inventory-to-csv

Walks a folder tree and writes a CSV inventory (path, size, MIME type, modified time, MD5) as the
`file_scan_table` deliverable. Requires the input `scan_root` (`Path`).

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
(both `Path`).

```
workflow-engine run --workflow-file examples/flatten-copy-tree.json \
  --input "source_root:Path=<folder-to-copy>" --input "target_dir:Path=<destination-folder>" --json
```

`--input NAME[:TYPE]=VALUE` is repeatable; `TYPE` names a registered codec (`help-components` lists
them). `set-input` only binds to a session that has not started yet; `run --input` binds and starts
in one call.

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
  preserving its relative artifact path.
- Run `export-artifact --session-id <SESSION_ID> --target-dir <dir> --all` (or `--artifact-name
  <name>` for one artifact) after the fact. Works for completed, paused and failed sessions.

`show-state --session-id <SESSION_ID>` renders the full persisted state: `parameters`, `outputs`,
`artifacts_absolute`, `deliverables` and `inputs`.

Exit codes: `0` success, `2` workflow paused, `3` workflow failed, `4` command-level setup or
resolution error. Full CLI and artifact contracts: `docs/architecture/overview.md`.

## Hitting the hard node cap

A recursive scan over a large tree can pause with `event_code: "workflow_paused_safety_limit"` (exit
code `2`) well before a short task flow would, because the hard node cap
(`docs/architecture/overview.md`, "Shape of a run") is one global number. Recovery: raise
`hard_max_nodes_visited` in the config file (see "Configuration file") and `resume` the session — the
run continues from where it paused. The cap's long-term scope (host vs. workflow vs. workflow class)
is open, tracked in
[`docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md`](docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md).

## Running the tests

Run tests from the repository root:

```
pytest
```

## Working on this project

Read `AGENTS.md` for the entry point into the project rules, and `docs/README.md` for the
documentation map.
