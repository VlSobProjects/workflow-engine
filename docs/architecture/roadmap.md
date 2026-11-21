# Roadmap

The steps of the current phase and the exit scenario of each phase. Read after
`docs/architecture/purpose.md` at the start of every architecture session.

Form: one sentence per row. A row is rewritten, not appended to. The content is expected to change;
the session that changes it records why in its session note. A phase is closed when its exit scenario
passes and every `open` note in `docs/architecture/notes/` has been triaged.

Only the current phase carries a step list; a later phase opens its list in the architecture session
that starts it.

## Phases

| Phase | Exit scenario | State |
| --- | --- | --- |
| 1 | The installed `workflow-engine` command runs a shipped template end to end and exports its deliverable (ADR 001–012, `v0.1.0`) | closed at the merge of `development` into `main` after the `v0.1.0` tag (2026-08-19) |
| 2 | The `load-test-triage` scenario, written by hand by an author deliberately working from the operator documentation alone, runs end to end on generated prepared data with a local model, its path chosen by the data, explained by the journal, and matching the numbers declared before the runs against the `fake`-adapter reference | current |
| 3 | Assisted authoring: blind authoring agents of different vendors, handed the same brief composed outside this repository, author a triage-class workflow through the published surfaces alone, at least one produced definition validating and running its expected path, with the divergence between agents measured by criteria declared beforehand | not started |
| publication | The phase 2 scenario runs live against a real system under test; a version flag and a delivery channel exist | not started |

The phase 2 hand-build claim carries its own evidence the way phase 3's blindness does: the session
note of the hand-build records that the author worked from the operator documentation alone, names
what was consulted, and records any step that needed more than it as a gap rather than patching it
silently — including, for every mistake made on the way, whether the error text led the author to
the fix. The claim is documentation sufficiency, not author blindness: the author knows the engine,
and blindness is what phase 3 buys with outside agents.

Phase 3 gates the authoring half of the done condition in `purpose.md`; its exit is an experiment
that must be runnable, so the enforcement of the answerer/operator split stays outside the phase —
the narrow entry plus a kept transcript is the blindness evidence — and a vendor agent that fails is
a data point, not a gate failure. The published surfaces its exit names include the
`workflow-authoring` flow: the agents author through that assisted cycle, which is the proof
`purpose.md` demands — a definition written directly from the documentation measures the floor, not
this exit. Its step list is opened when the phase starts; the work known to belong to it: ADR 019
into Implementing, the authoring surfaces (G11), the answerer/operator capability decision, the
`workflow-authoring` scenario, the `support-intake` note as a class 2 scenario, and the drift-A
experiment protocol.

The publication row gates a release — a version an operator can obtain and rely on — not the
visibility of the repository. The repository is readable in public from phase 2 on, as an engine in
progress with its status stated; a reader lands on the default branch `development`, and `main` stays
the line of marked stable states, merged at a phase close or a release.

## Phase 2 steps

Order as decided by `2026-08-23-architecture-1` §6, revised by `2026-08-24-architecture-1`, which
moved the output-family ADR ahead of ADR 014, by `2026-08-25-architecture-2`, which narrowed the
phase to the engine for hand-written workflows and moved the authoring work into phase 3, by
`2026-08-25-implementation-6`, which replaced the triage slice of step 10 with the class 4
measurement build, and by `2026-08-25-documentation-2`, which moved the debts, the notes triage and
a live-model rehearsal ahead of the data-generation work; the session notes record why.

| # | Step | State |
| --- | --- | --- |
| 1 | Interactive exchange: the `ask` node, computation inside it, template text, the visit cap and the read surfaces (ADR 013, 015–018) | done |
| 2 | Write `purpose.md`, its map row and the reading rule | done |
| 3 | Documentation system: consumer rule, scenarios as documents, this roadmap, registries rewritten | done in `2026-08-23-documentation-1` |
| 4 | Write the first class 2 scenario: the interview that creates a repository and its documents | done in `2026-08-23-documentation-2` |
| 5 | Write the class 2 exit-scenario document, so the `Consumer` of ADR 014 names an existing scenario | done in `2026-08-24-documentation-2` |
| 6 | Edit the Drafts: ADR 014 to the narrow Draft with its class 4 gate consumer, ADR 019 decoupled with the shared-mechanism guards | done in `2026-08-24-architecture-1` |
| 7 | The output-family ADR from the operator's `result-file-composition` note, checking rule 3 (one decision or two), then its implementation | done: ADR 020 opened in `2026-08-24-architecture-2`, implemented and accepted in `2026-08-24-implementation-1` |
| 8 | The node-record channel as its own ADR and its implementation first, then ADR 014 into Implementing and its implementation: the `llm` action and `fake` adapter in the core, the adapter package in this repository, the `described`/`tiered`/`chunked` variants of `folder-inventory-to-csv` as the freeze evidence | done: ADR 021 opened in `2026-08-24-architecture-3` and accepted in `2026-08-24-implementation-2`; ADR 014 implemented over six sessions and accepted in `2026-08-25-documentation-1` |
| 9 | Atomic state write and a session lock, one `fix/` session without an ADR, taken at any pause | done in `2026-08-25-implementation-4` |
| 10 | Build the plan half of the class 4 `reorganize-folder` example — code hashes and groups duplicates, a model classifies and plans, the plan exports as text and as a dictionary — measuring the answer-keys guard (G4), the dictionary half that remains of G5, the failure-route verbosity (G7) and whether inline template text carries a paragraph prompt | done in `2026-08-25-implementation-6` |
| 11 | One `refactor/` session for the code debts of the 2026-08-23 audit, and nothing beyond that list | done in `2026-08-25-implementation-7` |
| 12 | Notes maintenance: execute the triage decided by `2026-08-23-architecture-1` | done in `2026-08-25-documentation-3` |
| 13 | Run the `reorganize-folder` plan variant against a live local model as the rehearsal of the drift-B stack — the adapter, the JSON binding, the keys guard, the paragraph prompt — recording the findings and any prompt fixes, adding no feature | done in `2026-08-25-implementation-8`, with the two-provider residency fix split into `2026-08-25-implementation-9` |
| 14 | The data-generation discussion, then the dataset variants — real captures of a system under test under a real load rig, conditions induced for real, derived variants by window selection — with the domain parsing module and the declared thresholds of the drift-B protocol now carried by the scenario body | discussion done in `2026-08-26-architecture-1`; the rig work, the captures, the parsing module and the thresholds pending |
| 15 | Build the full exit scenario by hand on the generated variants and run the drift-B measurement that closes the phase | pending |
