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
4. Close the session with a git commit that includes the session note and related changes. If a session
   intentionally ends without a commit, state that explicitly in the session note with the reason.

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
| 2026-08-04 | architecture | Refined ADR 003 to keep work_dir mandatory at run level and move run start orchestration to engine.py until Session abstraction exists | completed | development | [2026-08-04-architecture-1_handoff.md](2026-08-04-architecture-1_handoff.md) |
| 2026-08-04 | architecture | Reviewed ADR 003 implementation, merged it to development, froze ADR 003 as Accepted, and opened ADR 004 for bootstrap/config snapshot follow-up | completed | development | [2026-08-04-architecture-2_handoff.md](2026-08-04-architecture-2_handoff.md) |
| 2026-08-04 | architecture | Audited architecture backlog, mapped missing ADR topics for implemented behavior, and prioritized follow-up drafts after ADR 004 | completed | development | [2026-08-04-architecture-3_handoff.md](2026-08-04-architecture-3_handoff.md) |
| 2026-08-04 | architecture | Drafted and refined ADR 005 in plugin-first scope (local manifest + external entry-point plugins) with concrete runtime loading architecture and implementation/testing criteria | completed | development | [2026-08-04-architecture-4_handoff.md](2026-08-04-architecture-4_handoff.md) |
| 2026-08-05 | architecture | Reviewed ADR 005 implementation, resolved blocking architecture defects, aligned the ADR text with delivered bootstrap loading, and froze ADR 005 as Accepted | completed | development | [2026-08-05-architecture-1_handoff.md](2026-08-05-architecture-1_handoff.md) |
| 2026-08-05 | architecture | Verified that ADR 005 did not close ADR 004, reduced ADR 004 to a per-session storage metadata record with lazy per-session storage resolution, and moved it to Implementing | completed | development | [2026-08-05-architecture-2_handoff.md](2026-08-05-architecture-2_handoff.md) |
| 2026-08-06 | implementation | Implemented ADR 004: a session records its storage settings and resumes from that record, with validated session records and per-session storage resolution | completed | feature/adr_004-session-bootstrap-and-config-snapshot | [2026-08-06-implementation-1_handoff.md](2026-08-06-implementation-1_handoff.md) |
| 2026-08-06 | architecture | Chose data flow between nodes as the next decision and opened ADR 006 as a draft with the open questions, the alternatives and the folder scan acceptance scenario | completed | development | [2026-08-06-architecture-1_handoff.md](2026-08-06-architecture-1_handoff.md) |
| 2026-08-06 | architecture | Settled ADR 006 data flow contract and moved the ADR to Implementing with explicit bus ownership, write semantics and scope boundaries | completed | development | [2026-08-06-architecture-2_handoff.md](2026-08-06-architecture-2_handoff.md) |
| 2026-08-07 | architecture | Added ADR 006 session control event journal contract and required external engine call auditability | completed | feature/adr_006-data-flow-between-nodes | [2026-08-07-architecture-1_handoff.md](2026-08-07-architecture-1_handoff.md) |
| 2026-08-08 | architecture | Reviewed ADR 006 implementation and set acceptance gate on missing component and e2e test coverage | completed | feature/adr_006-data-flow-between-nodes | [2026-08-08-architecture-1_handoff.md](2026-08-08-architecture-1_handoff.md) |
| 2026-08-08 | implementation | Added ADR 006 state contract tests and first recursive scan e2e scenario with artifact generation | completed | feature/adr_006-data-flow-between-nodes | [2026-08-08-implementation-1_handoff.md](2026-08-08-implementation-1_handoff.md) |
| 2026-08-08 | implementation | Refined ADR 006 scan e2e to use `FunctionsAction` and registered file metadata functions | completed | feature/adr_006-data-flow-between-nodes | [2026-08-08-implementation-2_handoff.md](2026-08-08-implementation-2_handoff.md) |
| 2026-08-09 | implementation | Stabilized ADR 006 session event persistence and control handling, then handed over remaining semantic gaps | interrupted | feature/adr_006-data-flow-between-nodes | [2026-08-09-implementation-1_handoff.md](2026-08-09-implementation-1_handoff.md) |
| 2026-08-09 | implementation | Fixed run-entry journaling semantics, terminal event persistence, and runtime cache/session isolation for ADR 006 | completed | feature/adr_006-data-flow-between-nodes | [2026-08-09-implementation-2_handoff.md](2026-08-09-implementation-2_handoff.md) |
| 2026-08-09 | implementation | Closed ADR 006 audit gaps: resume equivalence test, stale surfaces removal, and structured event details | completed | feature/adr_006-data-flow-between-nodes | [2026-08-09-implementation-3_handoff.md](2026-08-09-implementation-3_handoff.md) |
| 2026-08-09 | architecture | Accepted and froze ADR 006 after merge to development, closing setup-error journaling semantics as `workflow_setup_failed` | completed | development | [2026-08-09-architecture-1_handoff.md](2026-08-09-architecture-1_handoff.md) |
| 2026-08-09 | architecture | Opened ADR 007-010 drafts for phase 1 CLI release scope and aligned cheap architecture documentation corrections | completed | docs/adr_007-v1-foundation | [2026-08-09-architecture-2_handoff.md](2026-08-09-architecture-2_handoff.md) |
| 2026-08-11 | architecture | Accepted ADR 007 after aligning the public CLI contract with the delivered command surface and installed entry point | completed | development | [2026-08-11-architecture-2_handoff.md](2026-08-11-architecture-2_handoff.md) |
| 2026-08-11 | documentation | Synced the architecture overview with accepted ADRs and added the CLI contract to the current architecture view | completed | docs/architecture-overview-sync | [2026-08-11-documentation-1_handoff.md](2026-08-11-documentation-1_handoff.md) |
| 2026-08-11 | architecture | Finalized ADR 009 contract decisions for metadata ownership, JSON stability and acceptance-test policy | completed | development | [2026-08-11-architecture-4_handoff.md](2026-08-11-architecture-4_handoff.md) |
| 2026-08-11 | architecture | Moved ADR 009 to Implementing and opened its implementation branch | completed | development | [2026-08-11-architecture-5_handoff.md](2026-08-11-architecture-5_handoff.md) |
| 2026-08-18 | architecture | Froze ADR 009 as Accepted after merge to development and synchronized the registry and session note | completed | development | [2026-08-18-architecture-1_handoff.md](2026-08-18-architecture-1_handoff.md) |
| 2026-08-18 | implementation | Implemented ADR 010: a global hard safety cap (`hard_max_nodes_visited`, default 1000) that bounds every run and resume including soft-limit-0 sessions with a dedicated pause event | completed | feature/adr_010-session-safety-cap-and-unbounded-run-policy | [2026-08-18-implementation-4_handoff.md](2026-08-18-implementation-4_handoff.md) |
| 2026-08-18 | architecture | Reviewed ADR 010 implementation against requirements, merged to development, froze ADR 010 as Accepted, and synchronized documentation | completed | development | [2026-08-18-architecture-2_handoff.md](2026-08-18-architecture-2_handoff.md) |
| 2026-08-18 | investigation | Dogfooded the folder-to-CSV scenario as an operator; confirmed the artifact-access gap, the empty-root failure, and a broken CLI param-injection path; validated ADR 010 recovery; cleaned `examples/` to two validated templates | completed | docs/operator-scan-experiment | [2026-08-18-investigation-1_handoff.md](2026-08-18-investigation-1_handoff.md) |
| 2026-08-18 | architecture | Decided the artifact addressing and export contract (`artifact.` references, `deliverables` declaration with engine export on completion, `export-artifact` salvage command) and opened it as Draft ADR 011; fixed the stale ADR 010 registry row | completed | development | [2026-08-18-architecture-3_handoff.md](2026-08-18-architecture-3_handoff.md) |
| 2026-08-18 | implementation | Fixed the empty-root failure in `dict_list_to_pretty_table` (returns `pretty_table_no_data` instead of an opaque `IndexError`) with its first direct unit test; left the `resume` param-injection crash out of scope as phase-2 interactive input (ADR 007 §4); pinned a Bash-first shell convention in CLAUDE.md | completed | fix/empty-root-pretty-table | [2026-08-18-implementation-5_handoff.md](2026-08-18-implementation-5_handoff.md) |
| 2026-08-18 | implementation | Implemented ADR 011 end to end: `artifact.<name>` references, `copy_artifact`, `deliverables` declaration, engine export on completion, `export-artifact` command, and additive result keys; 176 tests pass | completed | feature/adr_011-artifact-addressing-and-export | [2026-08-18-implementation-6_handoff.md](2026-08-18-implementation-6_handoff.md) |
| 2026-08-18 | architecture | Verified ADR 011 implementation against requirements, merged feature branch into development, corrected Decision §1 wording, and froze ADR 011 as Accepted | completed | development | [2026-08-18-architecture-4_handoff.md](2026-08-18-architecture-4_handoff.md) |
| 2026-08-18 | architecture | Defined the phase 1 completion gate, chose session-bound typed workflow inputs over a template entity, and opened Draft ADR 012 with removal of the uncontracted resume flags | completed | development | [2026-08-18-architecture-5_handoff.md](2026-08-18-architecture-5_handoff.md) |
| 2026-08-18 | implementation | Implemented ADR 012: declared `inputs`, `set-input` command, one-shot `run --input`, codec-typed binding, required-input enforcement, and removal of uncontracted `resume` flags; 236 tests pass | completed | feature/adr_012-workflow-input-parameters | [2026-08-18-implementation-7_handoff.md](2026-08-18-implementation-7_handoff.md) |
| 2026-08-18 | architecture | Reviewed ADR 012 implementation against requirements, merged feature branch into development, and froze ADR 012 as Accepted | completed | development | [2026-08-18-architecture-6_handoff.md](2026-08-18-architecture-6_handoff.md) |
| 2026-08-18 | documentation | Introduced the architecture notes channel (`docs/architecture/notes/`) for durable ideas not yet decided, with fixed-header/free-body notes, a lifecycle and a registry; amended documentation-rules, git-workflow and adr-rules; captured the recovery roadmap and ADR 012 deferred-questions notes | completed | docs/architecture-notes-channel | [2026-08-18-documentation-1_handoff.md](2026-08-18-documentation-1_handoff.md) |

`Summary` states what the session was about, in one line.
`Status` is `completed` or `interrupted`.
An `interrupted` session must be picked up or explicitly closed before related work continues.
