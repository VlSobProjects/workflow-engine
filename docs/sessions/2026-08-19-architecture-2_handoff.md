# Session note

## Type
architecture

## Goal
Settle every open point of Draft ADR 013 and move it to Implementing, so the interactive exchange can
be built without further architecture work.

## Completion criteria
1. All five open points of ADR 013 are decided, each either as a decision section or as a recorded
   rejected alternative.
2. The contract gaps found by reading the ADR against the code are closed in the text.
3. ADR 013 is `Implementing` with its active branch named, and the registry row matches.
4. The notes ADR 013 intersects are updated, not left stale.

## Scope boundaries
- Documentation only; no runtime code changes and no implementation branch created.
- ADR 014 is not touched: its reuse of the answer declaration is unaffected by what was decided here.
- The retry/backoff ADR and the workflow-definition introspection ADR are not opened.

## Status
completed

## Result
ADR 013 is `Implementing` on `feature/adr_013-interactive-exchange`, with no open points left. The
Decision grew from six sections to nine: the three added ones state when an answer is refused, what
re-presenting a question means, and how the answer is journaled. Four rejected options were recorded
as alternatives E to H. One new architecture note records whether the external ADR-0083 questionnaire
scenarios are reachable on this engine.

## Decisions
All in `docs/adr/adr-013-interactive-exchange-contract.md`.

1. **The answer travels as JSON**, `resume --answer <json>` or `--answer-file <path>`. The `--input`
   flag grammar was rejected as the first transport (alternative F): an answer carries a status, a
   message and an actor beside its values, and a collection value would have to be JSON-parsed inside
   the flag string anyway. The flag form stays available later as an additive second transport.
2. **No `escalate` status and no `audience` hint** (alternative E). `resume` without an answer already
   re-presents the same node, consuming neither an attempt nor a visit; that is what an escalation
   needs. `audience` was a declaration the engine can neither check nor enforce.
3. **The caller-facing presentation is a reduced `question` block in `data`**, not `PresentResponse`
   (alternative G). The same class carries setup errors, budget stops, failures and completion;
   publishing it would make any change to those a breaking change of the command contract. This also
   records the fact that no presentation field reaches the caller today.
4. **An answer writes with `SET` only** (alternative H). An answer is a value, not an operation on the
   bus; accumulating answers across a loop is a following node's work with the existing
   collection-writing functions.
5. **An answer carries an optional `text`** which becomes the node's `output_text`. Without it a
   value guard cannot route on a free-form answer and `save_as` on an interactive node would store an
   empty string. The draft had not said what an answered node's output text is at all.
6. **An answer is refused unless the current node's action is interactive and the last event is
   `workflow_paused_interactive`.** Otherwise an answer to a node that did not ask is exactly the
   fabricated node output ADR 012 removed. A refusal applies nothing, journals nothing and exits 4,
   as a refused `set-input` already does.
7. **Two event codes, not three**, and the `actor` label rides in the event details:
   `SessionEvent.actor` stays the two-valued engine/operator distinction of ADR 006.
8. **No new state field.** `state.current_node_id` plus the built node's action type answer "where is
   the run paused"; the draft had listed a state marker as a possible cost.
9. **Counting needed no decision.** A re-presented question consumes neither an attempt nor a visit
   because that is what the engine already does; the consequence — the ADR 010 budget does not bound
   how long a question stays open — is recorded as intended.
10. **`describe-workflow` is not a prerequisite**, closing the open question the previous architecture
    session left. The answer declaration reaches the agent inside the presentation.
11. **Straight to Implementing, no POC.** The pause mechanism already exists and is covered by engine
    tests, so there is no question only code could answer.

## Open questions
- Whether text interpolation inside a string (`"the draft is <ref>, approve?"`) is worth introducing;
  today a reference resolves only as a whole configuration value. It blocks no ADR 013 scenario but
  costs an extra composing node in every "show the result back and ask" flow. Decided in ADR 014
  (prompt templating) or in the ADR 012 deferred §1 follow-up.
- Whether the budget checkpoint should be routed to a node inside the graph instead of the current
  out-of-graph pause. A change to ADR 010, not to ADR 013.

## Next steps
1. Implementation session: create `feature/adr_013-interactive-exchange` and build the decision,
   including `README.md`, `docs/architecture/overview.md` and an example workflow with an `ask` node.
2. Refine ADR 014 in Draft against the settled answer declaration.
3. Open the small `fix/` task for the atomic `state.json` write (recovery note (c)), still not done.
4. After ADR 013 is Accepted: the retry/backoff ADR (recovery note (b)) and the workflow-definition
   introspection ADR.

## References
- ADR: `docs/adr/adr-013-interactive-exchange-contract.md`, registry row in `docs/adr/README.md`
- Note opened: `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`
- Notes updated: `docs/architecture/notes/2026-08-18-recovery-and-resilience-roadmap.md`,
  `docs/architecture/notes/2026-08-18-adr012-deferred-questions.md`,
  `docs/architecture/notes/2026-08-19-node-save-as-redundancy.md`
- Previous session: `2026-08-19-architecture-1_handoff.md`
- Branch: `development`
