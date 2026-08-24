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
`completed`

## Result
All completion criteria are met.

- `models/node_record.py`: `NodeRecord` with the §1 shape and an open `details`, `TransitionRecord`,
  `ParamWriteRecord`, `RecordPage`, and the `RecordSource` contract, kept apart from `StateModel` so
  the split the ADR draws is visible in the code layout.
- `Storage` mixes in `RecordSource`; `JsonStorage` keeps `records.jsonl` beside `state.json`,
  appending one line per record and reading the stream line by line, filtering by node and bounding
  with a tail.
- The engine writes one record per concluded visit, after the state it describes is saved, and one
  for an entry refused by `max_visits`. A paused question concludes nothing and is recorded when its
  answer concludes it.
- `show-records --session-id <id> [--node <id>] [--tail <n>]` in the ADR 018 §3 discipline, with an
  operator form of one line per visit.
- Class 4 evidence run: `folder-inventory-to-csv` over a prepared tree of four files in three
  folders, 27 visits, read back whole, per node and tailed; written into the walkthrough under
  "Reading the walk back". `show-state` reports one guard result for `EMIT_CUR_PATH`, the trail
  holds all seven of its passes - which is the gap the ADR exists to close.
- Documentation carried in the branch: the ADR body and its change log, the walkthrough,
  `README.md`, `docs/architecture/overview.md` (Storage, State, the command list, the read surfaces,
  and a new "Node records" section).
- 42 tests added; `uv run pytest` 515 passed, `uv run ruff check .` clean, `uv run ruff format .`
  applied.

## Decisions
1. **A node output written through `save_as` is recorded as a write, under the mode `SAVE_AS`.**
   It reaches the state outside `param_writes`, and two of the three shipped examples produce values
   that way, so recording only the declared writes would have left the trail silent about the most
   common write. `StateModel.update` therefore returns what it applied. Recorded as an amendment in
   the ADR change log (`adr-rules.md` §5).
2. **The single §1 `writes` bullet became two members**, `writes` and `artifacts`: a list of write
   objects and a list of names are different shapes, and joining them for literal agreement with the
   text would have read worse. The transition likewise became a member of its own beside `guards`.
3. **The bounded read is an operation of the persistence contract**, not of the command that calls
   it, so a second storage implementation inherits the "node filter first, tail last" composition
   instead of every caller repeating it. The rejected alternative was the shape `show-journal` uses:
   hand the caller the whole stream and filter in the use case.
4. **The state is saved before its record is appended.** This is the ADR 021 §2 crash semantics made
   concrete: a trail missing its last record is an incomplete account of an exact run, while a record
   ahead of the state would account for effects that never took hold. A line that does not parse
   fails the read for the same reason.
5. **A visit whose action produced an error code is recorded as failed even when a guard routes the
   run onwards.** The status says what happened in the node, the transition says where the run went,
   and a retry loop reads back as the failures it actually made.

## Open questions
None. The ADR's own Leaves open list is unchanged: the `llm` details member (ADR 014 on its own
branch), retention, a schema version marker, and a rollback marker in the trail.

## Next steps
1. Merge this branch into `development`, set ADR 021 to Accepted there with its registry row, and
   add this session's row - the freeze gate holds: the walkthrough and the scenario registry list
   the ADR, the overview describes the delivered architecture, and the tests pass.
2. Roadmap step 8 continues: ADR 014 to `Implementing` and
   `feature/adr_014-llm-node-and-provider-adapter`, four sessions on one branch, amending ADR 014 §4
   to land the call audit in this channel as the `llm` details.
3. The `fix/` session for the atomic state write and the session lock stays its own concern; this
   decision made it cheaper, not different.

## References
- Branch: `feature/adr_021-node-record-channel`.
- Code: `models/node_record.py` (new), `models/state.py`, `storage/storage.py`,
  `storage/json_storage.py`, `engine.py`, `cli/contract.py`, `cli/use_cases.py`, `cli/presenters.py`,
  `cli/main.py`.
- Tests: `tests/test_adr021_node_records.py`, `tests/test_adr021_record_writing.py`,
  `tests/test_adr021_show_records.py` (all new).
- Documents changed: `docs/adr/adr-021-node-record-channel.md`,
  `examples/folder-inventory-to-csv.md`, `README.md`, `docs/architecture/overview.md`, this note.
- Related ADRs: ADR 021 (implemented here), ADR 002, ADR 003, ADR 006, ADR 010, ADR 011, ADR 013,
  ADR 017, ADR 018.
- Preceding note: `2026-08-24-architecture-3_handoff.md`.
