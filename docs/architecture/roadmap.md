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

Order as proposed by `2026-08-23-architecture-1` §6, to be revised by its pending decisions.

| # | Step | State |
| --- | --- | --- |
| 1 | Interactive exchange: the `ask` node, computation inside it, template text, the visit cap and the read surfaces (ADR 013, 015–018) | done |
| 2 | Write `purpose.md`, its map row and the reading rule | done |
| 3 | Documentation system: consumer rule, scenarios as documents, this roadmap, registries rewritten | done in `2026-08-23-documentation-1` |
| 4 | Write the first class 2 scenario: the interview that creates a repository and its documents | done in `2026-08-23-documentation-2` |
| 5 | ADR 014 back to a narrow Draft, decoupled from ADR 019; the first adapter as an external module; then Implementing | next |
| 6 | Atomic state write and a session lock, one `fix/` session without an ADR | pending |
| 7 | Write the exit scenario by hand on prepared data with the components that exist, to measure the output and handover gaps | pending |
| 8 | ADR 019 narrowed, after ADR 014 | pending |
| 9 | One `refactor/` session for the code debts of the 2026-08-23 audit, after ADR 019 | pending |
| 10 | Notes maintenance: triage every `open` note against the purpose | pending |
