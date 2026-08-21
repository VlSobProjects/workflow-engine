# Example workflows

The workflow templates shipped with the engine. Each is a definition the test suite runs end to end,
and each has its own walkthrough beside it.

| Template | What it does | Waits for an answer | Walkthrough |
| --- | --- | --- | --- |
| `folder-inventory-to-csv.json` | Walks a folder tree and writes a CSV inventory of the files it finds | no | [folder-inventory-to-csv.md](folder-inventory-to-csv.md) |
| `flatten-copy-tree.json` | Copies every file of a tree into one flat directory and reports what it copied | no | [flatten-copy-tree.md](flatten-copy-tree.md) |
| `approve-and-copy.json` | Asks for a decision, and copies the file only if the answer approves it | yes | [approve-and-copy.md](approve-and-copy.md) |

## What holds for all of them

- Each declares its `inputs`, so a run binds them before it starts: `run --input`, or `set-input`
  followed by `resume`.
- Each runs from any working directory the `workflow-engine` command is reachable from.
- Session data lands under `<cwd>/.workflow-engine/` unless the configuration file or `--work-dir`
  says otherwise.
- None of them reports success without its result: a node that cannot produce what the run declares
  fails under its own error code, and the run ends as a failed workflow.

The mechanics these walkthroughs use are defined once in the root [`README.md`](../README.md):
binding inputs, answering an interactive workflow, retrieving the result, and reading a session.
