# Roadmap

The steps of the current phase and the exit scenario of each phase. Read after
`docs/architecture/purpose.md` at the start of every architecture session.

Form: one sentence per row. A row is rewritten, not appended to. The content is expected to change;
the session that changes it records why in its session note. A phase is closed when its exit scenario
passes and every `open` note in `docs/architecture/notes/` has been triaged.

## Phases

| Phase | Exit scenario | State |
| --- | --- | --- |
| 1 | The installed `workflow-engine` command runs a shipped template end to end and exports its deliverable (ADR 001–012, `v0.1.0`) | closed at the merge of `development` into `main` after the `v0.1.0` tag (2026-08-19) |
| 2 | A fetch → aggregate → decide → branch → hand over workflow runs end to end on prepared data with a local model, its path chosen by the data and explained by the journal, written by an author who knows the domain but not the engine from the documentation alone | current |
| publication | The phase 2 scenario runs live against a real system under test; licence, version flag and delivery channel exist | not started |

## Phase 2 steps

Order as decided by `2026-08-23-architecture-1` §6 and revised by `2026-08-24-architecture-1`,
which moved the output-family ADR ahead of ADR 014; the session notes record why.

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
| 10 | Build the exit scenario by hand on prepared data, measuring the answer-shape and function-inventory gaps and the lower bound of the authoring need | pending |
| 11 | ADR 019 narrowed into Implementing; the `support-intake` note reformatted as a class 2 scenario beside it | pending |
| 12 | One `refactor/` session for the code debts of the 2026-08-23 audit, after ADR 019 | pending |
| 13 | Notes maintenance: execute the triage decided by `2026-08-23-architecture-1` | pending |
