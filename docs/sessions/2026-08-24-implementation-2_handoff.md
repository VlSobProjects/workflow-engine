# Session note: 2026-08-24 implementation 2

## Type
`implementation`

## Goal
Implement ADR 021: every node visit leaves an engine-written record in an append-only per-session
stream outside the state, read back by a bounded `show-records` command.

## Completion criteria
- A record model carries the ADR 021 §1 common shape — `record_id`, `timestamp`, `node_id`,
  `visit`, `attempt`, `action`, `status`, `guards`, `writes` — with an open `details` member, and
  carries names and codec names only, never values.
- The engine writes exactly one record per concluded visit, after the output is applied and the
  transition is chosen; a node refused on entry (ADR 017) is recorded as failed, and a visit that
  pauses is recorded when its answered visit concludes.
- The `Storage` contract gains the two operations of ADR 021 §2 — append one record, read records
  bounded — implemented in `JsonStorage` as a per-session JSON-lines file that is only ever
  appended to.
- `show-records --session-id <id> [--tail <n>] [--node <node_id>]` publishes the stream as
  persisted in the ADR 018 §3 discipline: whole without flags, `--node` filters first, `--tail`
  bounds last, the answer reports carried against held, `--tail` below `1` is a command error,
  exit `0` on success and `4` on resolution errors.
- The class 4 evidence is run: `folder-inventory-to-csv` over a prepared tree, its walk read back
  whole, per node and tailed, documented in the walkthrough.
- The ADR body describes what was delivered, with every departure from the Draft in its change log;
  `README.md` and `docs/architecture/overview.md` match the delivered surface.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- The `llm` details member stays undefined here: ADR 014 defines it on its own branch (a Draft may
  not constrain a Draft).
- `show-journal` and `state.session_events` are untouched; no per-visit event codes enter the
  journal.
- No payload in records: the definition-declared `record: true` artifact opt-in of ADR 021 §3
  belongs to ADR 014.
- Roadmap step 9 — the atomic state write and the session lock — stays its own `fix/` concern.
- No retention, rotation or schema version marker; the ADR 010 cap bounds a session's stream.

## Status
`interrupted`

## Result
Opened only. ADR 021 was moved to `Implementing` on `development` and this branch was created; no
code has been written yet.

## Decisions
None yet.

## Open questions
- The stream file name and the record's serialized field set are the implementation's choice
  (ADR 021 Implementation notes); both are documented in the walkthrough when the evidence is run.

## Next steps
1. Implement the record model and the two storage operations, then the engine write point.
2. Add `show-records` in the ADR 018 §3 discipline.
3. Run the class 4 evidence on `folder-inventory-to-csv` and carry the walkthrough, `README.md`,
   `docs/architecture/overview.md` and the ADR body in this branch.
4. Merge into `development`, set ADR 021 to Accepted there, and register this session.

## References
- Branch: `feature/adr_021-node-record-channel`.
- Related ADRs: ADR 021 (implemented here), ADR 002, ADR 003, ADR 006, ADR 010, ADR 011, ADR 013,
  ADR 017, ADR 018.
- Preceding note: `2026-08-24-architecture-3_handoff.md`.
