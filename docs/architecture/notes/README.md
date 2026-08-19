# Architecture notes

A durable place for architectural ideas, insights and tensions that outlive a session and precede a
decision. A note captures a thought before it is ripe for an ADR, so it is not lost and can be picked
up deliberately later.

This is the single sanctioned channel for in-repo architectural thinking. It does not reopen the ban on
ad hoc reports, summaries, plans or work logs (`documentation-rules.md` §7): those stay forbidden. Only
notes in this directory, in the format below, are allowed.

## What a note is, and is not

| Belongs in | When |
| --- | --- |
| a **note** | an architectural idea or observation that outlives the current session and is not yet a decision |
| a **session note** (`docs/sessions/`) | thoughts within the scope of the current task |
| an **ADR** (`docs/adr/`) | the idea has matured into a decision, with alternatives and consequences |
| the **overview** (`docs/architecture/overview.md`) | the architecture as it is actually built now |

A note is not: a session summary, a task tracker, a decision, current-state documentation, or a working
log. It is a thinking space, not reference documentation.

## Structure

A note has a fixed header and a free body. Copy `template.md`.

- The header fields are mandatory and uniform: `Date`, `Trigger`, `Status`, `Affected`.
- The body is free: prose, lists, schemas, competing options, open discussion — any form. Unlike
  reference documentation, a note is not held to the "short declarative, one topic" format rule; its job
  is to hold thinking, not to be tidy.

## Lifecycle

A note is never silently forever-open. Its `Status` is one of:

- `open` — captured, not yet resolved.
- `promoted` — became an ADR or landed in the overview; record where (e.g. `promoted → ADR 013`).
- `dropped` — decided against or obsolete; record the reason in one line.

Terminal notes (`promoted`, `dropped`) are kept as the idea trail, the same way ADR history is kept.
They are exempt from `documentation-rules.md` §6 "remove superseded documentation".

## Naming

`YYYY-MM-DD-<short-name>.md`, the date the note was opened. The file name carries no status; the registry
below is the index. Lowercase ASCII and hyphens.

## Commit policy

Capture is meant to be frictionless. A note may be committed at any moment, in its own commit, with no
tests and no linter (it is prose). The note file may be committed directly to `development` or on any
work branch. The registry row is reconciled on `development` when the branch merges, the same rule the
session and ADR registries follow. See `docs/processes/git-workflow.md`.

## How notes are consumed

Notes are only useful if they are read. During architecture work (see `docs/rules/adr-rules.md`):

- A free-scope architecture session ("what architectural work is open?") draws its candidates from the
  `open` notes here.
- When a discussed ADR intersects a note, it is an obligation to either update the note's `Affected` link
  or change its `Status` (`promoted`/`dropped`). A note is not left stale next to a decision that touched it.

## Registry

The registry is the only index of notes. A note missing from it is effectively lost. Add the row when the
branch merges into `development`.

| Date | Summary | Status | Affected | Link |
| --- | --- | --- | --- | --- |
| 2026-08-18 | Recovery and resilience roadmap for phase 2 and beyond: retry/backoff, manual takeover via interactive node output, snapshot-based rollback with operator-registered compensation | open | ADR 006, ADR 007, ADR 012 | [2026-08-18-recovery-and-resilience-roadmap.md](2026-08-18-recovery-and-resilience-roadmap.md) |
| 2026-08-18 | Deferred architectural questions from ADR 012 implementation: shallow reference resolution, Python-version-dependent codec names, and the missing workflow-definition introspection surface | open | ADR 006, ADR 009, ADR 011, ADR 012 | [2026-08-18-adr012-deferred-questions.md](2026-08-18-adr012-deferred-questions.md) |
| 2026-08-19 | Scope of the hard node cap: keep the global `hard_max_nodes_visited` default for phase 1, and weigh a workflow-declared or workflow-type-derived cap later | open | ADR 007, ADR 010, ADR 012 | [2026-08-19-hard-node-cap-scoping.md](2026-08-19-hard-node-cap-scoping.md) |
| 2026-08-19 | Entry-point discovery for component registration, deferred out of the ADR 005 implementation freeze: conflict policy, name-only vs. module-qualified registries, precedence and operator auditability | open | ADR 005 | [2026-08-19-entry-point-discovery.md](2026-08-19-entry-point-discovery.md) |
| 2026-08-19 | Node level `save_as` duplicates `state.outputs`, which `output.<node_id>` already reads: whether the key can retire, and what would have to replace author-chosen parameter naming | open | ADR 006, ADR 009 | [2026-08-19-node-save-as-redundancy.md](2026-08-19-node-save-as-redundancy.md) |
