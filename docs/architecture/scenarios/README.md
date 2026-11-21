# Scenarios

A scenario is a task the engine is measured against: who answers each step, what data goes in, which
paths through the data are expected, and how it ends. Scenarios are written before the decisions they
need; architecture and investigation sessions find the decisions a scenario lacks.

## Classes

| Class | What it is | Where it lives |
| --- | --- | --- |
| 2 | An external task written in full, with prepared input data | `docs/architecture/scenarios/<name>.md` |
| 4 | A shipped example: its walkthrough in `examples/` carries the same header | one registry row here, pointing to the walkthrough |

The class of tasks in `docs/architecture/purpose.md` is not a scenario and does not filter work.
Synthetic end to end tests in `tests/` check nodes through a real agent; they are not scenarios and are
not evidence at the ADR freeze gate.

## Structure

A scenario has a stable identifier, the fixed header of `template.md` and a free body. The header
fields are mandatory: `Identifier`, `Class`, `Answerers`, `Input data`, `Expected paths`, `Ends with`,
`ADRs exercised`.

## Scenario and ADR

Scenario and ADR relate many-to-many. The list `ADRs exercised` in the scenario is the one truth for
the relation, because an accepted ADR cannot be edited. A new ADR names the scenario in its `Consumer`
section, and the scenario adds the ADR to its list in the same session. The freeze gate in
`docs/adr/process.md` takes its evidence from a scenario of class 2 or 4.

## Variants

One example with named variants replaces several that derive from one another. Every named variant is
covered by a test or marked as not verified in the walkthrough.

## Naming

Class 2: `<short-name>.md`, lowercase ASCII and hyphens; the identifier is the file name without
extension. Class 4: the identifier is the template name in `examples/`.

## Registry

The registry is the only index of scenarios. A row is one sentence. Add the row when the branch merges
into `development`.

| Identifier | Class | Summary | ADRs exercised | Link |
| --- | --- | --- | --- | --- |
| `repository-interview` | 2 | An agent interviews the human and creates the repository and documents that seed the consuming project's development loop | ADR 011, 013, 015, 016, 017, 018, 019, 020 | [repository-interview.md](repository-interview.md) |
| `folder-inventory-to-csv` | 4 | Walks a folder tree and writes what it finds twice: the flat `file_scan_table` CSV for a machine and the `file_scan_report` document, a table per folder, for a reader; ships in the three named variants `described`, `tiered` and `chunked`, in which a model writes what each file contains, proposes what to do with the inventory, and reads a file too large for it part by part | ADR 002, 006, 011, 012, 014, 020, 021, 022 | [folder-inventory-to-csv.md](../../../examples/folder-inventory-to-csv.md) |
| `flatten-copy-tree` | 4 | Copies every file of a tree into one flat directory and reports what it copied as the `copy_report` deliverable | ADR 002, 006, 011, 012 | [flatten-copy-tree.md](../../../examples/flatten-copy-tree.md) |
| `approve-and-copy` | 4 | Asks for a decision and copies the file only if the answer approves it | ADR 002, 006, 012, 013, 016 | [approve-and-copy.md](../../../examples/approve-and-copy.md) |
| `workflow-authoring` | 2 | A universal cycle in which a human or an agent authors any workflow definition node by node, validated without being run | ADR 007, 009, 011, 012, 013, 015, 016, 017, 018 | [workflow-authoring.md](workflow-authoring.md) |
| `reorganize-folder` | 4 | Audits a folder tree — files hashed and duplicates grouped in code, a model classifying each file and composing the reorganization plan as prose and as a moves dictionary, the plan checked by the answer-keys guard before it lands | ADR 002, 006, 011, 012, 014, 016, 020, 021 | [reorganize-folder.md](../../../examples/reorganize-folder.md) |
| `load-test-triage` | 2 | The phase 2 exit scenario: a fully automatic triage of one prepared load-test run in which local models aggregate and decide, code confirms, and the human receives the verdict or the handover | ADR 005, 006, 011, 012, 014, 016, 017, 018, 020, 021, 022 | [load-test-triage.md](load-test-triage.md) |
| `payment-reconciliation` | 2 | A per-document reconciliation of payment documents against bank statements in which code matches and guarantees, a local model extracts and scores, and a person submits the certain entries and reviews every scored match, with an evaluation contour outside the engine | ADR 005, 006, 011, 012, 013, 014, 016, 017, 018, 020, 021 | [payment-reconciliation.md](payment-reconciliation.md) |
| `model-call-reading` | 2 | A reading of `llm-test-bench`'s example task over a one-node `llm` definition under the `fake` adapter, then a recount with no session, listing every engine surface the bench takes and marking the session's copy of the definition as an implementation detail | ADR 005, 007, 011, 012, 014, 017, 018, 021 | [model-call-reading.md](model-call-reading.md) |
