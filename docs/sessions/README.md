# Sessions

A session is one narrow piece of work with a declared goal and a declared end.
Every session produces exactly one note in this directory.

## Session types

Closed list. A session has exactly one type.

| Type | Used for |
| --- | --- |
| `architecture` | Decisions captured as ADRs |
| `implementation` | Code changes |
| `documentation` | Documentation and rules |
| `investigation` | Research that changes no code |
| `maintenance` | Dependencies, tooling, repository hygiene |

## File naming

`YYYY-MM-DD-<type>-<n>_handoff.md`

- The date is the day the session started.
- `<type>` is the session type from the list above.
- `<n>` counts the sessions of that type on that day, starting at `1`, and is always present.
- Example: `2026-08-02-documentation-1_handoff.md`

The file name carries no description on purpose. Do not infer the content of a session from its name.
To find a session, read the registry below; sessions of one type are read in order.

## Lifecycle

1. At the start, create the session file with its type, goal and completion criteria.
2. During the session, keep the scope inside those criteria.
3. At the end, complete the file with the result, the decisions and the next steps.

A session that is interrupted still leaves its file, marked `interrupted`.

## Where it lives

- The session file is written in the working branch and lands with the work it describes.
- A session that produces no code still uses a branch, normally under `docs/`.
- The registry row below is added on `development` when the branch is merged.

## Content limits

- Record facts, decisions and next steps. Do not retell the course of the work.
- No code dumps, no command output, no logs.
- If the scope grew during the session, record the split and leave the rest to the next steps.

## Registry

The registry is the only index of sessions. The file names carry no description, so a session that is
missing from the registry is effectively lost. Add the row when the branch is merged.

| Date | Type | Summary | Status | Branch | Link |
| --- | --- | --- | --- | --- | --- |
| 2026-08-02 | documentation | Established the project rules and the documentation system, and brought the repository into a clean state | completed | development | [2026-08-02-documentation-1_handoff.md](2026-08-02-documentation-1_handoff.md) |
| 2026-08-02 | architecture | Captured the node model as ADR 002 and reduced it from three layers to one action with guarded transitions | completed | docs/adr_002-node-composition | [2026-08-02-architecture-1_handoff.md](2026-08-02-architecture-1_handoff.md) |
| 2026-08-02 | implementation | Implemented ADR 002, reviewed it, and fixed the defects the review and the code reading found | completed | feature/adr_002-node-composition | [2026-08-02-implementation-1_handoff.md](2026-08-02-implementation-1_handoff.md) |
| 2026-08-03 | architecture | Reviewed ADR 001 implementation, resolved blocking defects, merged to development, and froze ADR 001 as Accepted | completed | feature/adr-001-exception-architecture | [2026-08-03-architecture-1_handoff.md](2026-08-03-architecture-1_handoff.md) |

`Summary` states what the session was about, in one line.
`Status` is `completed` or `interrupted`.
An `interrupted` session must be picked up or explicitly closed before related work continues.
