# Example workflows

The workflow templates shipped with the engine. Each is a definition the test suite runs end to end,
and each has its own walkthrough beside it.

| Template | What it does | Waits for an answer | Walkthrough |
| --- | --- | --- | --- |
| `folder-inventory-to-csv.json` | Walks a folder tree and writes a CSV inventory of the files it finds | no | [folder-inventory-to-csv.md](folder-inventory-to-csv.md) |
| `flatten-copy-tree.json` | Copies every file of a tree into one flat directory and reports what it copied | no | [flatten-copy-tree.md](flatten-copy-tree.md) |
| `approve-and-copy.json` | Asks for a decision, and copies the file only if the answer approves it | yes | [approve-and-copy.md](approve-and-copy.md) |
| `reorganize-folder.json` | Audits a folder tree — hashes, duplicate groups, a category per file — and delivers a reorganization plan as prose and as a moves dictionary | no | [reorganize-folder.md](reorganize-folder.md) |

`folder-inventory-to-csv` ships in three named variants beside the base definition. A variant is a
run of its own, not a mode of one file, and the three are covered by the one walkthrough of the
template they vary — the "Variants" section of
[folder-inventory-to-csv.md](folder-inventory-to-csv.md):

| Variant | What it adds |
| --- | --- |
| `folder-inventory-to-csv-described.json` | A `Description` column a model writes for the file formats the input lists |
| `folder-inventory-to-csv-tiered.json` | The same, and a second model composing an optimization proposal over the finished table |
| `folder-inventory-to-csv-chunked.json` | The same, and the split-and-accumulate branch for a file the model refuses as too large |

## What holds for all of them

- Each declares its `inputs`, so a run binds them before it starts: `run --input`, or `set-input`
  followed by `resume`.
- Each runs from any working directory the `workflow-engine` command is reachable from.
- Session data lands under `<cwd>/.workflow-engine/` unless the configuration file or `--work-dir`
  says otherwise.
- None of them reports success without its result: a node that cannot produce what the run declares
  fails under its own error code, and the run ends as a failed workflow.

The three variants and `reorganize-folder` add one condition the others do not have: they call a
model, so the engine configuration file has to name a provider before any of them runs. What that takes is in "Calling a
model" in the root [`README.md`](../README.md), and what these definitions expect of it is in the
walkthrough. Under `pytest` they run on the `fake` adapter and reach no network.

The mechanics these walkthroughs use are defined once in the root [`README.md`](../README.md):
binding inputs, answering an interactive workflow, retrieving the result, and reading a session.
