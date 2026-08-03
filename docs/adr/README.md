# ADR index

This directory holds the architecture decision records and their registry.

## ADR registry

| ID | Title | Status | Summary | Depends on | Active branch | Link |
| --- | --- | --- | --- | --- | --- | --- |
| 001 | Exception architecture | Accepted | One exception root split into configuration and runtime errors, with runtime failures normalized to engine exceptions and configuration errors aggregated by node before execution | — | — | [adr-001-exception-architecture.md](adr-001-exception-architecture.md) |
| 002 | Node composition — one action and guarded transitions | Accepted | A node is one action plus an ordered list of guarded transitions; guards replace validators, stay boolean, receive no state, and their named results are recorded in the state | — | — | [adr-002-node-composition.md](adr-002-node-composition.md) |
| 003 | The boundary between persistence and the working directory | Draft | Persistence of the definition and the state is a medium neutral contract over dictionaries; the working directory is a separate concept and stays a real directory | — | — | [adr-003-persistence-and-workspace.md](adr-003-persistence-and-workspace.md) |

Keep this table updated on every status change.
The registry is edited only on `development`.

## ADR governance
- `template.md` — the section structure of an ADR.
- `format.md` — formatting and status values.
- `process.md` — lifecycle, transitions, freeze gate and git linkage.
- `../rules/adr-rules.md` — rules for discussing and changing ADRs.
