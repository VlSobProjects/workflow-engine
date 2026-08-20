# Session note

## Type
architecture

## Goal
Decide the session read surfaces — `show-state` narrowed to the state of the run, parameters and the
journal given their own bounded read commands — and capture the decision as an ADR draft.

## Completion criteria
1. The five questions recorded in "What the session that takes this on has to decide" of
   `docs/architecture/notes/2026-08-20-interview-continuation-context.md` are each answered or
   explicitly deferred, in critical mode with alternatives and costs.
2. An ADR 018 draft exists in `docs/adr/` with its registry row, written on `development` as the ADR
   process requires for a draft.
3. The continuation note's `Status`/`Affected` reflect the outcome (promoted into the ADR or updated).
4. This session note is completed and committed.

## Scope boundaries
- No implementation: the ADR is drafted, not built. Implementation is its own session under the ADR
  branch when the draft moves to Implementing.
- The rejected shape — embedding prior-exchange context in the published question — is not reopened
  (`docs/architecture/notes/2026-08-20-question-rendering-for-an-audience.md`).
- Whether the engine should keep a transcript of the exchange (values, against ADR 013 §9) is not
  decided here beyond recording where it stands.
- ADR 014 and the other open notes stay untouched.

## Status
completed

## Result
ADR 018 "Session read surfaces" drafted (`docs/adr/adr-018-session-read-surfaces.md`) with its
registry row. All five questions of the continuation note are answered inside it; the note is marked
`promoted → ADR 018`, and the `2026-08-18-adr012-deferred-questions.md` note gains ADR 018 in its
`Affected` — the `inputs` removal sharpens its missing-introspection point. No code changed.

## Decisions
All belong to ADR 018 (Draft); recorded here as the session's outcome.
1. **`show-state` shows the state of the run, and nothing else.** It keeps status, last event,
   errors, current node, counters and budget, plus artifacts and deliverables (bounded by the
   workflow's declaration, and the one surface telling a late caller what to fetch), and additively
   gains the guard traces (bounded by construction). `parameters`, `outputs` and `inputs` leave.
   The journal was never in the result and stays out — only the last event code remains.
2. **Parameters split into `list-parameters` and `show-parameter`**, one result shape each; the names
   follow the existing `list-`/`show-` verbs. Plain output renders by the ADR 016 rule; `--json`
   carries the codec envelope as persisted, so a value round-trips into `set-input` of another
   session. An unknown name is a command error, exit `4`, like `help-component`.
3. **The journal gets `show-journal`, unbounded by default** — asking for the journal is an explicit
   act — with `--tail` and `--node` as the optional bound and filter; `--code`/`--since` wait for a
   scenario. This amends the note's leaning toward a default bound, at the operator's direction.
4. **One ADR carries the whole boundary**, journal command included: "and nothing else" holds only if
   the journal has its own door.
5. **The transcript question is not answered by this ADR** and is recorded there as deferred: a read
   surface publishes what is persisted, and the journal stores no values (ADR 013 §9).

## Open questions
1. Where the declared-inputs interface is read after it leaves `show-state` — the missing
   workflow-definition introspection surface of `2026-08-18-adr012-deferred-questions.md`, now
   sharpened.
2. Whether `outputs` gets a dedicated surface; removed without replacement until a scenario asks.
3. Whether the three artifact spellings in `show-state` consolidate while the result is breaking
   anyway (flagged in the ADR's implementation notes).

## Next steps
1. Move ADR 018 to Implementing when its turn comes: `feature/adr_018-session-read-surfaces`,
   carrying the CLI changes, the tests, `README.md` and `docs/architecture/overview.md`.
2. ADR 014 as its turn comes (unchanged from the previous session's next steps).
3. Friction 3, the script-running function for `S`, as an external module (unchanged).

## References
- Branch: `development` (ADR draft per `docs/adr/process.md` git linkage)
- Added: `docs/adr/adr-018-session-read-surfaces.md`
- Changed: `docs/adr/README.md`, `docs/architecture/notes/README.md`,
  `docs/architecture/notes/2026-08-20-interview-continuation-context.md`,
  `docs/architecture/notes/2026-08-18-adr012-deferred-questions.md`
- Subject note: `docs/architecture/notes/2026-08-20-interview-continuation-context.md`
- Previous session: `2026-08-20-implementation-5_handoff.md`
