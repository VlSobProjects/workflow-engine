# Session note

## Type
implementation

## Goal
Implement ADR 018: narrow `show-state` to the state of the run and add the three bounded read
commands — `list-parameters`, `show-parameter`, `show-journal`.

## Completion criteria
1. `show-state` no longer returns `parameters`, `outputs` or `inputs`, and additively returns
   `guard_results`; `deliverables` and the three artifact spellings stay.
2. `list-parameters`, `show-parameter --name` and `show-journal [--tail] [--node]` exist as info
   commands: exit `0` on command success regardless of workflow status, `4` on an unknown name.
3. Tests cover every new surface and the removals; `uv run pytest` and `uv run ruff check .` pass
   from the command line.
4. `README.md` and `docs/architecture/overview.md` describe the delivered read surfaces.
5. The ADR body records what was built, and this session note is completed and committed.

## Scope boundaries
- Only the read side of the CLI. Nothing about how state is persisted changes.
- `inputs` stays in the `run`, `resume` and `set-input` results; ADR 018 removes it from `show-state`
  only.
- The three artifact spellings in `show-state` are kept as the ADR decided; consolidating them is not
  reopened here.
- The deferred transcript question and the missing workflow-definition introspection surface stay
  open.

## Status
completed

## Result
All five criteria met. `StateReadOnlyView` gained four readers over what the state already keeps
(guard traces, the parameter listing, one parameter as its persisted envelope, the journal); the CLI
gained the three commands as info commands, each rendering its own plain output and carrying one
shape of `data` under `--json`. `show-state` lost `parameters`, `outputs` and `inputs` and gained
`guard_results`. `tests/test_adr018_read_surfaces.py` covers the four surfaces end to end against the
shipped `approve-and-copy` template, including the envelope feeding `set-input` of another session;
the one existing test that asserted the old `show-state` shape was rewritten to assert the new one.
Verified from the command line: `uv run ruff check .` clean, `uv run pytest` 458 passed.

## Decisions
Four points ADR 018 left to the implementation, all recorded in its change log:
1. **`CONTRACT_VERSION` does not move**, against the draft's implementation note. The only such
   constant versions the operator help payloads (ADR 009) and is stamped into nothing this change
   touches; raising it would announce a change to help consumers that did not happen. Whether command
   results should carry a version of their own stays open.
2. **`show-parameter --json` carries the name and the writing node beside the codec envelope**, the
   same two fields `list-parameters` publishes, so one value can be read without also calling the
   listing.
3. **`show-journal` reports the size of its answer next to the size of the whole journal**, and
   refuses a `--tail` below `1` as a command error: a bounded read that does not say it is bounded
   reads as the full record, and an empty answer would read as an empty journal.
4. **Each command renders its own plain output** rather than falling back to the generic `Data: {...}`
   line, as the help surfaces already do. A journal printed as one Python dict is not a surface a
   human reads.

## Open questions
1. The published `type` of a parameter is the registered codec name, a fully qualified Python name
   that the interpreter can change (`pathlib.Path` reads as `pathlib._local.Path` on 3.13). It is now
   contract on two surfaces (`list-parameters` and the `object_type` of the envelope) and it already
   was in `state.json`; whether the registry should key codecs by a stable name is untouched.
2. Where the declared-inputs interface is read now that it left `show-state` — the missing
   workflow-definition introspection surface of `2026-08-18-adr012-deferred-questions.md`, unchanged
   by this session.
3. Whether `outputs` gets a dedicated surface; removed without replacement until a scenario asks.

## Next steps
1. Merge the branch into `development`, check the ADR 018 freeze gate and set the ADR to Accepted
   with its registry row.
2. ADR 014 as its turn comes.
3. Friction 3, the script-running function for `S`, as an external module.

## References
- Branch: `feature/adr_018-session-read-surfaces`
- ADR: `docs/adr/adr-018-session-read-surfaces.md`
- Added: `tests/test_adr018_read_surfaces.py`
- Changed: `src/workflow_engine/models/state.py`, `src/workflow_engine/cli/contract.py`,
  `src/workflow_engine/cli/use_cases.py`, `src/workflow_engine/cli/main.py`,
  `src/workflow_engine/cli/presenters.py`, `tests/test_cli_contract.py`, `README.md`,
  `docs/architecture/overview.md`
- Previous session: `2026-08-20-architecture-7_handoff.md`
