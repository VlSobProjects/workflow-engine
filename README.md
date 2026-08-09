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

## Running the tests

Run tests from the repository root:

```
pytest
```

## Working on this project

Read `AGENTS.md` for the entry point into the project rules, and `docs/README.md` for the
documentation map.
