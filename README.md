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

## Running the examples

`examples/` ships two validated templates. Each declares its `inputs` and its deliverable, and runs
from any working directory with `uv run workflow-engine ...`. Session data lands under
`<cwd>/.workflow-engine/` unless overridden with `--work-dir`.

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
absolute path in its `data`:

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
- Read the absolute `path` directly from that output.
- Pass `--export-dir <dir>` to `run` or `resume`, exporting the deliverables on completion.
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
`hard_max_nodes_visited` in the engine configuration file
(default `<cwd>/.workflow-engine/workflow_engine_config.json`) and `resume` the session — the run
continues from where it paused. The cap's long-term scope (host vs. workflow vs. workflow class) is
open, tracked in
[`docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md`](docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md).

## Running the tests

Run tests from the repository root:

```
pytest
```

## Working on this project

Read `AGENTS.md` for the entry point into the project rules, and `docs/README.md` for the
documentation map.
