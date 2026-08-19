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
| 2026-08-11 | implementation | Implemented ADR 008: shared `--work-dir`/`--storage-dir` CLI options, the config discovery order, and POSIX path serialization for the runtime directory policy | completed | feature/adr_008-runtime-directory-and-default-path-policy-for-v1 | [2026-08-11-implementation-1_handoff.md](2026-08-11-implementation-1_handoff.md) |
| 2026-08-11 | architecture | Ran the ADR 007 acceptance review, resolved command-surface and exit-code disputes, and recorded the blocking gaps left before freeze | completed | feature/adr_007-cli-contract-and-session-lifecycle-for-v1 | [2026-08-11-architecture-1_handoff.md](2026-08-11-architecture-1_handoff.md) |
| 2026-08-11 | architecture | Accepted ADR 007 after aligning the public CLI contract with the delivered command surface and installed entry point | completed | development | [2026-08-11-architecture-2_handoff.md](2026-08-11-architecture-2_handoff.md) |
| 2026-08-11 | documentation | Synced the architecture overview with accepted ADRs and added the CLI contract to the current architecture view | completed | docs/architecture-overview-sync | [2026-08-11-documentation-1_handoff.md](2026-08-11-documentation-1_handoff.md) |
| 2026-08-11 | architecture | Refined ADR 008 into a concrete v1 policy for the runtime root, work directory, JsonStorage directory, config discovery order, override precedence and setup-error handling | completed | development | [2026-08-11-architecture-3_handoff.md](2026-08-11-architecture-3_handoff.md) |
| 2026-08-11 | architecture | Finalized ADR 009 contract decisions for metadata ownership, JSON stability and acceptance-test policy | completed | development | [2026-08-11-architecture-4_handoff.md](2026-08-11-architecture-4_handoff.md) |
| 2026-08-11 | architecture | Moved ADR 009 to Implementing and opened its implementation branch | completed | development | [2026-08-11-architecture-5_handoff.md](2026-08-11-architecture-5_handoff.md) |
| 2026-08-11 | architecture | Corrected ADR 009's metadata model to separate developer docstrings from operator-facing help and defined per-component-type sources for detailed help | completed | feature/adr_009-operator-help-and-component-introspection-contract | [2026-08-11-architecture-6_handoff.md](2026-08-11-architecture-6_handoff.md) |
| 2026-08-11 | architecture | Refined ADR 009 with a dedicated help-contract module architecture, a WorkflowNode-oriented detail schema, explicit CLI coupling boundaries and concrete freeze acceptance boundaries | completed | feature/adr_009-operator-help-and-component-introspection-contract | [2026-08-11-architecture-7_handoff.md](2026-08-11-architecture-7_handoff.md) |
| 2026-08-18 | implementation | Closed the gap between the `help_contract` implementation and ADR 009 by deciding contested contract details and wiring CLI help commands to the builder only | completed | feature/adr_009-operator-help-and-component-introspection-contract | [2026-08-18-implementation-1_handoff.md](2026-08-18-implementation-1_handoff.md) |
| 2026-08-18 | implementation | Replaced test-local `adr006_*` helper registrations in the ADR 006 e2e tests with reusable core components, proven by a new recursive copy-tree e2e | completed | feature/adr_009-operator-help-and-component-introspection-contract | [2026-08-18-implementation-2_handoff.md](2026-08-18-implementation-2_handoff.md) |
| 2026-08-18 | implementation | Added a `help-component` type-level mode (component list and description per type) alongside the unchanged `help-components` automation contract | completed | feature/adr_009-operator-help-and-component-introspection-contract | [2026-08-18-implementation-3_handoff.md](2026-08-18-implementation-3_handoff.md) |
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
| 2026-08-19 | implementation | Closed the minor operator findings: top-level `session_id` for `init-new-session`, BOM-tolerant UTF-8 JSON IO, CSV artifacts without blank rows; replaced the personal-path example with a `tmp_path` test fixture | completed | fix/minor-operator-findings | [2026-08-19-implementation-1_handoff.md](2026-08-19-implementation-1_handoff.md) |
| 2026-08-19 | documentation | Added a README how-to for running the two example templates end to end, retrieving the result, the CLI exit codes and the hard node cap recovery | completed | docs/readme-run-and-retrieve-howto | [2026-08-19-documentation-1_handoff.md](2026-08-19-documentation-1_handoff.md) |
| 2026-08-19 | documentation | Extended the README with the config file, deliverable export mechanics and custom component registration, and brought the repository to `ruff format` cleanliness; closes phase 1 completion gate item 3 | completed | development | [2026-08-19-documentation-2_handoff.md](2026-08-19-documentation-2_handoff.md) |
| 2026-08-19 | investigation | Audited the architecture overview, README, ADRs, registries and repository state against the code before the phase 1 release; recorded 8 unregistered session notes, a silent `copy_file` misbehaviour behind the `flatten-copy-tree` how-to, and overview/ADR/process imprecisions as the fix list before tagging `v0.1.0` | completed | docs/phase1-release-audit | [2026-08-19-investigation-1_handoff.md](2026-08-19-investigation-1_handoff.md) |
| 2026-08-19 | documentation | Applied the documentation-only findings from the phase 1 pre-release audit: registered 8 missing sessions, synced the overview with the code, fixed stale ADR cross-references and template deviations, resolved the process.md/git-workflow.md contradiction, completed session note headings, and added CLAUDE.md to the document map | completed | docs/phase1-audit-doc-fixes | [2026-08-19-documentation-3_handoff.md](2026-08-19-documentation-3_handoff.md) |
| 2026-08-19 | documentation | Closed the audit's open question on preventive rules: made overview synchronization a condition of the ADR freeze gate, and recorded why the registry, session-heading and README-precondition classes get observation or a code fix instead of a rule | completed | development | [2026-08-19-documentation-4_handoff.md](2026-08-19-documentation-4_handoff.md) |
| 2026-08-19 | implementation | Made the file copy target an explicit choice: `copy_file` takes only a full target path, copying into a folder moved to `copy_file_to_folder`, both refusing a missing or wrong target with their own error codes instead of silently overwriting one file | completed | fix/copy-file-target-semantics | [2026-08-19-implementation-2_handoff.md](2026-08-19-implementation-2_handoff.md) |
| 2026-08-19 | implementation | Corrected the operator help of the four core actions, which declared the node key `save_as` as an action parameter, and removed the dead `BaseAction.save_as` field and the pass-through constructors it left behind | completed | fix/action-metadata-save-as | [2026-08-19-implementation-3_handoff.md](2026-08-19-implementation-3_handoff.md) |
| 2026-08-19 | investigation | Ran the final pre-release audit of `development`: tests/lint clean, all previous audit findings closed or deferred, README flows re-executed; recorded one candidate blocker (failed runs print `Engine stop:` to stdout, breaking `--json`) and post-tag follow-ups; verdict: no gate-blocking finding | completed | docs/phase1-final-audit | [2026-08-19-investigation-2_handoff.md](2026-08-19-investigation-2_handoff.md) |
| 2026-08-19 | implementation | Removed the three `Engine stop:` prints that made `run --json` of a failed workflow unparseable, and made the run commands carry the engine response errors so an exception escaping an action still names its cause | completed | fix/engine-stop-stdout | [2026-08-19-implementation-4_handoff.md](2026-08-19-implementation-4_handoff.md) |
| 2026-08-19 | implementation | Gave both shipped templates a failure transition before the end of the run, so a missing CSV deliverable or a failed copy ends as a failed workflow with its error code instead of exit 0; added the first end-to-end coverage of `examples/` | completed | fix/template-failure-transitions | [2026-08-19-implementation-5_handoff.md](2026-08-19-implementation-5_handoff.md) |
| 2026-08-19 | documentation | Applied the documentation findings of the final phase 1 audit: overview statements on set-limit, guard names, attempts, inputs, config creation and help detail keys re-checked against the code; README preconditions and the Windows path note; rules index, section numbering and the meaning of the ADR registry's `Depends on` | completed | docs/phase1-audit-doc-followups | [2026-08-19-documentation-5_handoff.md](2026-08-19-documentation-5_handoff.md) |
| 2026-08-19 | investigation | Collected the defects still open after the `v0.1.0` tag, each re-checked against the tagged code, and grouped them into four fix sessions; found one new contract defect: a malformed command line writes help to stdout and never produces JSON | completed | docs/v0_1_0-fix-shortlist | [2026-08-19-investigation-3_handoff.md](2026-08-19-investigation-3_handoff.md) |
| 2026-08-19 | implementation | Closed the two CLI JSON contract gaps of the `v0.1.0` shortlist: a malformed command line now reports on stderr and answers `--json` with a `CommandResult`, and `run`/`resume` report the deliverable export destination in `data.export` | completed | fix/cli-json-contract-gaps | [2026-08-19-implementation-6_handoff.md](2026-08-19-implementation-6_handoff.md) |

`Summary` states what the session was about, in one line.
`Status` is `completed` or `interrupted`.
An `interrupted` session must be picked up or explicitly closed before related work continues.
