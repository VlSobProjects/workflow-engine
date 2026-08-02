# ADR index

This directory holds the architecture decision records and their registry.

## ADR registry

| ID | Title | Status | Summary | Depends on | Active branch | Link |
| --- | --- | --- | --- | --- | --- | --- |
| 001 | Exception architecture | Draft | One exception root split into configuration and runtime errors, with context added as an error travels up, and all configuration errors reported before start | — | — | [adr-001-exception-architecture.md](adr-001-exception-architecture.md) |
| 002 | Node composition — one action and guarded transitions | Implementing | A node is one action plus an ordered list of guarded transitions; guards replace validators, stay boolean, and their named results are recorded in the state | — | `feature/adr_002-node-composition` | [adr-002-node-composition.md](adr-002-node-composition.md) |

Keep this table updated on every status change.
The registry is edited only on `development`.

## ADR governance
- `template.md` — the section structure of an ADR.
- `format.md` — formatting and status values.
- `process.md` — lifecycle, transitions, freeze gate and git linkage.
- `../rules/adr-rules.md` — rules for discussing and changing ADRs.
