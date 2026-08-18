# ADR index

This directory holds the architecture decision records and their registry.

## ADR registry

| ID | Title | Status | Summary | Depends on | Active branch | Link |
| --- | --- | --- | --- | --- | --- | --- |
| 001 | Exception architecture | Accepted | One exception root split into configuration and runtime errors, with runtime failures normalized to engine exceptions and configuration errors aggregated by node before execution | — | — | [adr-001-exception-architecture.md](adr-001-exception-architecture.md) |
| 002 | Node composition — one action and guarded transitions | Accepted | A node is one action plus an ordered list of guarded transitions; guards replace validators, stay boolean, receive no state, and their named results are recorded in the state | — | — | [adr-002-node-composition.md](adr-002-node-composition.md) |
| 003 | The boundary between persistence and the working directory | Accepted | Persistence of the definition and the state is a medium neutral contract over dictionaries; run bootstrap moved to session layer, with bootstrap/config snapshot deferred to ADR 004 | — | — | [adr-003-persistence-and-workspace.md](adr-003-persistence-and-workspace.md) |
| 004 | Session bootstrap and configuration snapshot | Accepted | A session records its storage settings in `session.json` inside its session directory, and resume builds storage from that record instead of the current global configuration | 003, 005 | — | [adr-004-session-bootstrap-and-config-snapshot.md](adr-004-session-bootstrap-and-config-snapshot.md) |
| 005 | Component loading and plugin registration model | Accepted | Bootstrap loads built-in core modules and configured external modules before execution, making registration deterministic and auditable | 004 | — | [adr-005-component-loading-and-registration.md](adr-005-component-loading-and-registration.md) |
| 006 | Data flow between nodes | Accepted | The engine owns the journal and applies typed parameter write sets into a persisted flat bus, with explicit overwrite policy, artifact registration, and deterministic resume semantics | 002, 003, 004 | — | [adr-006-data-flow-between-nodes.md](adr-006-data-flow-between-nodes.md) |
| 007 | CLI contract and session lifecycle for v1 | Accepted | Define the first stable command-line contract to create sessions, run/resume workflows, update soft limits, and return machine-readable outcomes | 004, 005, 006 | — | [adr-007-cli-contract-and-session-lifecycle-for-v1.md](adr-007-cli-contract-and-session-lifecycle-for-v1.md) |
| 008 | Runtime directory and default path policy for v1 | Accepted | Define deterministic defaults and override rules for `work_dir` and `JsonStorage` roots from CLI calls | 003, 004, 007 | — | [adr-008-runtime-directory-and-default-path-policy-for-v1.md](adr-008-runtime-directory-and-default-path-policy-for-v1.md) |
| 009 | Operator help and component introspection contract | Accepted | Define operator-facing help surfaces for actions, functions, guards and codecs with deterministic output shape | 005, 007 | — | [adr-009-operator-help-and-component-introspection-contract.md](adr-009-operator-help-and-component-introspection-contract.md) |
| 010 | Session safety cap and unbounded run policy | Accepted | Define an engine-wide hard node budget and its interaction with per-session soft limits to prevent unbounded runs | 006, 007, 008 | — | [adr-010-session-safety-cap-and-unbounded-run-policy.md](adr-010-session-safety-cap-and-unbounded-run-policy.md) |
| 011 | Artifact addressing and export contract | Draft | Artifacts become the declared deliverables of a workflow: engine-resolved `artifact.` references, engine export on completion to an operator destination, and CLI surfacing and extraction for every run outcome | 006, 007, 008, 009 | — | [adr-011-artifact-addressing-and-export.md](adr-011-artifact-addressing-and-export.md) |

Keep this table updated on every status change.
The registry is edited only on `development`.

## ADR governance
- `template.md` — the section structure of an ADR.
- `format.md` — formatting and status values.
- `process.md` — lifecycle, transitions, freeze gate and git linkage.
- `../rules/adr-rules.md` — rules for discussing and changing ADRs.
