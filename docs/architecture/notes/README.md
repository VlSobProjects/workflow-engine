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
| 2026-08-18 | Recovery and resilience roadmap for phase 2 and beyond: retry/backoff, manual takeover via interactive node output, snapshot-based rollback with operator-registered compensation | open | ADR 006, ADR 007, ADR 012, ADR 013, ADR 014 | [2026-08-18-recovery-and-resilience-roadmap.md](2026-08-18-recovery-and-resilience-roadmap.md) |
| 2026-08-18 | Deferred architectural questions from ADR 012 implementation: shallow reference resolution, Python-version-dependent codec names, and the missing workflow-definition introspection surface | open | ADR 006, ADR 009, ADR 011, ADR 012, ADR 013, ADR 014, ADR 018 | [2026-08-18-adr012-deferred-questions.md](2026-08-18-adr012-deferred-questions.md) |
| 2026-08-19 | Scope of the hard node cap: keep the global `hard_max_nodes_visited` default for phase 1, and weigh a workflow-declared or workflow-type-derived cap later | open | ADR 007, ADR 010, ADR 012, ADR 017 | [2026-08-19-hard-node-cap-scoping.md](2026-08-19-hard-node-cap-scoping.md) |
| 2026-08-19 | Entry-point discovery for component registration, deferred out of the ADR 005 implementation freeze: conflict policy, name-only vs. module-qualified registries, precedence and operator auditability | open | ADR 005 | [2026-08-19-entry-point-discovery.md](2026-08-19-entry-point-discovery.md) |
| 2026-08-19 | Node level `save_as` duplicates `state.outputs`, which `output.<node_id>` already reads: whether the key can retire, and what would have to replace author-chosen parameter naming | open | ADR 006, ADR 009, ADR 013 | [2026-08-19-node-save-as-redundancy.md](2026-08-19-node-save-as-redundancy.md) |
| 2026-08-19 | How an operator obtains the `workflow-engine` command on Windows, macOS and Linux: the wheel installs and runs a workflow end to end, but has no delivery channel, carries no examples, states no licence and reports no version; the PyPI name is taken and no run has ever happened off Windows | open | ADR 005, ADR 007, ADR 008 | [2026-08-19-installation-and-distribution.md](2026-08-19-installation-and-distribution.md) |
| 2026-08-19 | Whether the questionnaire scenarios of the external ADR-0083 node graph are reachable here: its six node types collapse into three, and after re-measuring the mapping against the delivered ADR 015, ADR 016 and ADR 017 the core gap is closed — a question carries its value inside the sentence, the node that asks checks what it bound, and a node bounds its own re-entry. The surfacing and the accumulating post function are in the core as component work under ADR 015, and the scenario has folded onto them from eleven nodes to seven — the predicted count, measured. What is left is an in-graph budget checkpoint, the final process-specific step settled as a plugin rather than a core component, and one question the fold raised: whether a guard may read a value the current output is about to write. The yardstick for the first goal of phase 2 | open | ADR 005, ADR 010, ADR 012, ADR 013, ADR 014, ADR 015, ADR 016, ADR 017, ADR 018 | [2026-08-19-adr0083-scenarios-coverage.md](2026-08-19-adr0083-scenarios-coverage.md) |
| 2026-08-19 | Where the interactive exchange stops being internal: the ADR 013 review found the internal/published boundary held by one function rather than by the shapes, `actor` as an audit label with no identity contract, and a published `question` block with no version of its own | open | ADR 007, ADR 009, ADR 013, ADR 014 | [2026-08-19-interactive-exchange-publishing-boundary.md](2026-08-19-interactive-exchange-publishing-boundary.md) |
| 2026-08-20 | Rendering the published question for its audience: a registered renderer over a typed `QuestionBlock` class produces the text for one reader (human, small model, vendor format), chosen by the consumer rather than the node, pure and additive to the machine contract; a full-context processor is recorded as rejected in three shapes with the trigger to reconsider | open | ADR 005, ADR 009, ADR 013, ADR 014 | [2026-08-20-question-rendering-for-an-audience.md](2026-08-20-question-rendering-for-an-audience.md) |
| 2026-08-19 | Whether the engine can carry a team's development process, where people and agents walk one graph of the team's rules: what it already carries, and the four tensions under it — concurrent access to a session versus parallel nodes, delivery of components with the workplace, identity at the transport boundary, and where the local pre-flight ends and the pipeline begins | open | ADR 002, ADR 003, ADR 004, ADR 005, ADR 006, ADR 010, ADR 013 | [2026-08-19-engine-as-team-process-carrier.md](2026-08-19-engine-as-team-process-carrier.md) |
| 2026-08-20 | How an answerer that comes back reads the context of an interrupted exchange: an interrupted interview already costs nothing, but the journal and the guard traces leave no command, reading is all-or-nothing, and the engine keeps no record of the exchange itself. The context is pulled through read commands rather than pushed into the published question, which stays rejected; `show-state` narrows to the state of the run while parameters, the journal and possibly the outputs get their own bounded surfaces, under an ADR because removing `parameters` is a removal | promoted → ADR 018 | ADR 006, ADR 009, ADR 013, ADR 018 | [2026-08-20-interview-continuation-context.md](2026-08-20-interview-continuation-context.md) |
| 2026-08-21 | The first use case that is a reason to adopt the engine — an agent taking a technical-support call to a handover a human operator can act on — measured against the component inventory: no function creates a dictionary parameter, a composed artifact name is inexpressible because template text is confined to the ten presentation fields of `ask`, the single output shape is a table in six syntaxes while the handover is a structured ticket, and nothing checks that an answered dictionary carries the items the question declared; 19 of the 28 registered functions are filesystem work. Proposed as a required exit condition of phase 2, which cannot be recorded as a decision because no document holds the phase plan | open | ADR 005, ADR 011, ADR 013, ADR 014, ADR 016 | [2026-08-21-support-intake-use-case.md](2026-08-21-support-intake-use-case.md) |
| 2026-08-21 | One instruction that lets an agent drive any workflow without being told what it is: because it may not mention the scenario, writing it measures whether the published question block and the command result are self-sufficient — and the agent cannot see what a re-ask costs it in attempts. The document map admits no such document, and `AGENTS.md` is the wrong home because it addresses an agent working on this repository rather than one using the engine; the Skill destination is recorded here for the first time, against a project that still has no delivery channel | open | ADR 007, ADR 009, ADR 013, ADR 016, ADR 018 | [2026-08-21-agent-instruction-and-skill.md](2026-08-21-agent-instruction-and-skill.md) |
| 2026-08-21 | The published question block states what to answer and never how: the answer envelope of ADR 013 §4 lives in `README.md` and the overview, not in the block, while `generic_error_code` is published — so half the return contract crosses the publishing boundary and an answerer holding only the paused result cannot compose a valid answer; `node_id` meanwhile is published to a reader who cannot use it, since `resume` addresses a session and not a node. Adapting the answer's form to its audience turns out to be unrecorded rather than decided: the rendering idea covers the question only, and the one renderer in the tree formats the internal class it was told not to consume | open | ADR 005, ADR 009, ADR 013 | [2026-08-21-answer-document-and-its-audience.md](2026-08-21-answer-document-and-its-audience.md) |
| 2026-08-21 | What one paused command result costs the model that has to answer it: the instruction three times, the status three times, the node id and the session id twice each, the session-constant fields on every turn, the empty fields always, and a `data.timestamp` that is the state's creation time and never moves. Underneath the size is a contract question — neither ADR 007 nor ADR 013 says who the payload is addressed to, so nothing may be dropped from it today; the options run from stopping `description` defaulting into the result message to splitting the answerer's document from the operator's telemetry | open | ADR 007, ADR 013, ADR 018 | [2026-08-21-command-result-cost-for-a-machine-reader.md](2026-08-21-command-result-cost-for-a-machine-reader.md) |
