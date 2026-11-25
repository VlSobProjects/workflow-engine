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

A note that is amended a third time is closed or split. A note does not declare its phase: the triage
in an architecture session assigns it, and a phase is not closed while an `open` note is untriaged
(`docs/architecture/roadmap.md`).

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
branch merges into `development`. A row is one sentence; the thinking is in the note.

The registry has four sections. The `Status` header of the note is the only truth; a note moves between
sections without moving its file. An `open` note is listed under "Not triaged" until an architecture
session assigns it a phase.

### Current phase

| Date | Summary | Status | Affected | Link |
| --- | --- | --- | --- | --- |
| 2026-08-25 | Two different measurements under one claim — drift B, one definition across providers, is the phase 2 protocol (roadmap steps 13–15); drift A, one brief across authoring agents, is encoded in the phase 3 exit | open | ADR 011, ADR 013, ADR 014, ADR 017, ADR 021 | [2026-08-25-two-drifts-and-their-measurement.md](2026-08-25-two-drifts-and-their-measurement.md) |
| 2026-11-21 | The engine has no human-readable account of a run: a `report` command writing one self-contained HTML document from the read surfaces, its first consumer a CI demonstration published on Pages, authoring by an agent skill weighed as the floor | open | ADR 022, ADR 007, ADR 009, ADR 018, ADR 020, ADR 021 | [2026-11-21-run-report-and-public-showcase.md](2026-11-21-run-report-and-public-showcase.md) |

### Later phases

| Date | Summary | Status | Affected | Link |
| --- | --- | --- | --- | --- |
| 2026-08-25 | Two roles at the engine's boundary — the answerer who walks the nodes and the operator who owns the session — the capability decision assigned to phase 3, enforcement outside the process and outside the phase gate | open | ADR 003, ADR 004, ADR 007, ADR 008, ADR 018, ADR 019 | [2026-08-25-role-separation-answerer-and-operator.md](2026-08-25-role-separation-answerer-and-operator.md) |
| 2026-08-25 | A version number that states the era, the phase and the fix, assigned to the publication phase where the exit row already names the version flag | open | ADR 007, `docs/adr/process.md`, `documentation-rules.md` §6 | [2026-08-25-version-numbering-and-architecture-eras.md](2026-08-25-version-numbering-and-architecture-eras.md) |
| 2026-08-18 | Recovery and resilience beyond phase 1: crash-safe state write delivered, retry/backoff still "not now", snapshot rollback with compensation stays after phase 2 | open | ADR 006, ADR 007, ADR 012, ADR 013, ADR 014, ADR 021 | [2026-08-18-recovery-and-resilience-roadmap.md](2026-08-18-recovery-and-resilience-roadmap.md) |
| 2026-08-18 | Questions deferred from the ADR 012 implementation: shallow reference resolution, the codec-name question settled inside ADR 019, no definition introspection surface (the G11 authoring work of phase 3) | open | ADR 006, ADR 009, ADR 011, ADR 012, ADR 013, ADR 014, ADR 018, ADR 019 | [2026-08-18-adr012-deferred-questions.md](2026-08-18-adr012-deferred-questions.md) |
| 2026-08-19 | Whether the hard node cap stays a global default or becomes workflow-declared, waiting on real numbers from more scenarios | open | ADR 007, ADR 010, ADR 012, ADR 017 | [2026-08-19-hard-node-cap-scoping.md](2026-08-19-hard-node-cap-scoping.md) |
| 2026-08-19 | Entry-point discovery for component registration, deferred out of ADR 005: conflict policy, naming, precedence, auditability | open | ADR 005 | [2026-08-19-entry-point-discovery.md](2026-08-19-entry-point-discovery.md) |
| 2026-08-19 | How an operator obtains the command on each OS: no delivery channel, no version, PyPI name taken; the licence settled as MIT — the publication gate | open | ADR 005, ADR 007, ADR 008 | [2026-08-19-installation-and-distribution.md](2026-08-19-installation-and-distribution.md) |
| 2026-08-19 | Where the interactive exchange stops being internal: §1 and §3 promoted in part into ADR 019 §2, `actor` identity (§2) stays open beside the role-separation note above | open | ADR 007, ADR 009, ADR 013, ADR 014, ADR 019 | [2026-08-19-interactive-exchange-publishing-boundary.md](2026-08-19-interactive-exchange-publishing-boundary.md) |
| 2026-08-19 | Whether the engine can carry a team's development process, and the four tensions under it — a later application, not the purpose | open | ADR 002, ADR 003, ADR 004, ADR 005, ADR 006, ADR 010, ADR 013 | [2026-08-19-engine-as-team-process-carrier.md](2026-08-19-engine-as-team-process-carrier.md) |
| 2026-08-21 | The support-intake use case measured against the component inventory: four gaps in dictionary parameters, template text, output shape and answer checking — reformatted as a class 2 scenario in phase 3, ADR 019's second consumer | open | ADR 005, ADR 011, ADR 013, ADR 014, ADR 016, ADR 020 | [2026-08-21-support-intake-use-case.md](2026-08-21-support-intake-use-case.md) |
| 2026-08-21 | One instruction that lets an agent drive any workflow, which measures whether the published block and the command result are self-sufficient; acts after ADR 019 reaches Implementing, Skill deferred to the publication gate | open | ADR 019, ADR 007, ADR 009, ADR 013, ADR 016, ADR 018 | [2026-08-21-agent-instruction-and-skill.md](2026-08-21-agent-instruction-and-skill.md) |
| 2026-08-28 | Rendered dashboard panels as input for image-capable models — an image channel for the `llm` node would be an ADR across the action, the adapter contract and the record channel, and sits in extended measurement outside the phase gate | open | ADR 014, ADR 016, ADR 021 | [2026-08-28-rendered-panels-as-model-input.md](2026-08-28-rendered-panels-as-model-input.md) |

### Not triaged

| Date | Summary | Status | Affected | Link |
| --- | --- | --- | --- | --- |
| 2026-08-28 | Phase 3 assisted authoring extended to component authoring — functions, guards and codecs as a testable authored artifact, the model cost paid once at authoring time | open | ADR 005, ADR 009 | [2026-08-28-authoring-extends-to-components.md](2026-08-28-authoring-extends-to-components.md) |
| 2026-08-28 | Determinism required of the boundary, not the step — a model step normalized by a post-function and routed by deterministic guards, the journal as the specification of a future replacement function | open | ADR 002, ADR 014, ADR 021 | [2026-08-28-boundary-determinism-function-vs-model.md](2026-08-28-boundary-determinism-function-vs-model.md) |
| 2026-11-21 | The engine writes its published contract — command line, definition format, component API — and a consumer asks for a change by a request letter; checked by tests that also accept a second storage backend, the pin becoming a version range | open | ADR 005, ADR 007, ADR 009, ADR 011, ADR 012, ADR 014, ADR 018, ADR 021 | [2026-11-21-published-contract-and-consumer-requests.md](2026-11-21-published-contract-and-consumer-requests.md) |
| 2026-11-21 | The facts about a session every storage backend gives a read-only reader, whatever it stores them in — the definition and the session record without a surface today, the writes kept with the engine | open | ADR 003, ADR 004, ADR 007, ADR 008, ADR 018, ADR 021, ADR 022, `purpose.md` | [2026-11-21-storage-read-contract.md](2026-11-21-storage-read-contract.md) |
| 2026-11-25 | The report replaces the home directory by `~` in the values only, and the journal details — the destination of `artifacts_exported` among them — keep it, so a published report can name its operator | open | ADR 022, ADR 018, ADR 020 | [2026-11-25-report-home-in-journal-details.md](2026-11-25-report-home-in-journal-details.md) |
| 2026-11-25 | A second public demonstration with a model: a digest of public technical documentation — pages fetched, summarized by an `llm` node under a declared window, delivered as a PDF — a class 4 example whose fetch, extraction and PDF live in an external module, run from CI against the owner's Ollama host | open | ADR 014, ADR 020, ADR 022 | [2026-11-25-documentation-digest-showcase.md](2026-11-25-documentation-digest-showcase.md) |

### Closed

| Date | Summary | Status | Affected | Link |
| --- | --- | --- | --- | --- |
| 2026-08-24 | The operator cannot read the flat one-table output of a run: result files need composition — grouped tables, authored document shapes, template text outside `ask` | promoted → ADR 020 | ADR 006, ADR 011, ADR 016, ADR 020 | [2026-08-24-result-file-composition.md](2026-08-24-result-file-composition.md) |
| 2026-08-20 | A registered renderer over a typed question block produces the text for one reader, chosen by the consumer | promoted → ADR 019 | ADR 005, ADR 009, ADR 013, ADR 014 | [2026-08-20-question-rendering-for-an-audience.md](2026-08-20-question-rendering-for-an-audience.md) |
| 2026-08-20 | How an answerer that comes back reads the context of an interrupted exchange: pulled through bounded read commands, not pushed into the question | promoted → ADR 018 | ADR 006, ADR 009, ADR 013, ADR 018 | [2026-08-20-interview-continuation-context.md](2026-08-20-interview-continuation-context.md) |
| 2026-08-21 | The published question block states what to answer and never how, so an answerer holding only the paused result cannot compose a valid answer | promoted → ADR 019 | ADR 005, ADR 009, ADR 013 | [2026-08-21-answer-document-and-its-audience.md](2026-08-21-answer-document-and-its-audience.md) |
| 2026-08-21 | What one paused command result costs a machine reader, and that no ADR says who the payload is addressed to | promoted → ADR 019 | ADR 007, ADR 013, ADR 018 | [2026-08-21-command-result-cost-for-a-machine-reader.md](2026-08-21-command-result-cost-for-a-machine-reader.md) |
| 2026-08-19 | Whether the external ADR-0083 questionnaire scenarios are reachable here, re-measured against ADR 015–017: the core gap is closed, an in-graph budget checkpoint and a guard reading a pending write are the two residuals recorded inside the note | promoted → ADR 015, 016, 017 | ADR 005, ADR 010, ADR 012, ADR 013, ADR 014, ADR 015, ADR 016, ADR 017, ADR 018 | [2026-08-19-adr0083-coverage.md](2026-08-19-adr0083-coverage.md) |
| 2026-08-19 | Whether node level `save_as` can retire, since `output.<node_id>` already reads `state.outputs`: no consumer asks for it | dropped (re-raised by the output-family ADR of G6 — ADR 020 — or a scenario that needs author-named outputs) | ADR 006, ADR 009, ADR 013 | [2026-08-19-node-save-as-redundancy.md](2026-08-19-node-save-as-redundancy.md) |
