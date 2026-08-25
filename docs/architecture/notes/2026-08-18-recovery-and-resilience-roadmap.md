# Recovery and resilience roadmap

- **Date:** 2026-08-18
- **Trigger:** discussion during the ADR 012 implementation session about long AI-agent workflows that
  are interrupted (e.g. a Claude API 500) and cannot be moved forward, while an operator could do the
  step by hand.
- **Status:** open
- **Affected:** ADR 006 (bus/journal invariants), ADR 007 (§4 interactive input deferred to phase 2),
  ADR 012 (pre-start binding; deliberately closed off mid-run external writes), ADR 013
  (Accepted, carries (a) — session `2026-08-19-architecture-2`; (b) is unblocked now that ADR 014
  is delivered, (c) is a small fix without an ADR — session `2026-08-19-architecture-1`), ADR 014
  (Accepted; delivered the error classes (b) will consume — sessions `2026-08-21-architecture-1`,
  `2026-08-25-architecture-1`), ADR 021
  (Accepted; the append-only node-record trail (d) assumes to stay audit-complete across a rollback,
  with the rollback marker left open there — session `2026-08-24-architecture-3`)

## The gap

The engine persists state every turn, so an interrupted run stops at a clean node boundary. What is
missing is a sanctioned way to *move a stopped run forward* when the automated step cannot complete —
without editing state by hand. ADR 012 closed off external bus writes to a started run on purpose;
recovery must reintroduce its own surface deliberately, not widen `set-input`.

"Recovery" is not one feature. It decomposes into capabilities with very different cost:

- **(a) Manual takeover via interactive node output.** The operator supplies the `ActionNodeOutput`
  (including `param_writes`) the node could not produce. This is architecturally clean: all bus writes
  still come from a node output, applied by the engine and journaled — the ADR 006 invariant stays
  intact. It is the phase-2 interactive-answer mechanism (ADR 007 §4). Cost: medium.
- **(b) Retry with backoff by error class.** Partly exists (`max_attempts` / `attempt_counters`, a
  self-loop transition). Missing: delay/backoff and distinguishing transient (500 → retry) from
  permanent (400 → fail). Central for API-driven agents. Cost: low. This subsumes the former overview
  "what is not settled yet" item — the error and retry policy beyond a transition's declared allowance.
- **(c) Crash-safe state write.** Delivered by roadmap step 9 (session
  `2026-08-25-implementation-4`): `state.json` is written to a temporary file in the same directory
  and renamed onto the target, so an interrupted write leaves the previous state readable. The same
  session gave a run exclusive hold of its session, which is the other half of "nothing else writes
  this file behind our back".
- **(d) Rollback to a checkpoint.** The only genuinely new subsystem. Today state is a single mutable
  snapshot; the journal is audit, not a source the state is rebuilt from. Rollback needs either a
  snapshot history (version `state.json` per node visit instead of overwriting — restore points, like
  Windows) or event sourcing (truncate + replay the journal). Snapshot history is the cheaper path and
  pairs with the existing per-turn write. On rollback, do not truncate the journal: append a
  `rolled_back_to N` event so the journal stays append-only and audit-complete; the snapshot is what
  reverts. Cost: high.
- **(e) External-world compensation.** Rolling internal state back does not undo side effects (files
  created outside the workflow, external calls). Boundary: the engine owns internal state; the operator
  registers compensation/rollback scripts for external effects. Caveat: rollback + re-run still needs
  those scripts to fully reset external state, else re-run double-applies. Cost: high, but scoped to the
  operator.

## Design points to preserve for (a), when phase 2 builds it

1. The operator-supplied output routes through the node's guards/transitions, not around them, so the
   graph stays consistent.
2. Journal it under a distinct actor (operator-supplied output) so audit separates "engine computed"
   from "operator supplied".
3. Distinguish pause from fail. Continuing a paused interactive node is easy. A run in terminal
   `FAILED` that the operator wants to finish by hand is a new capability — "reopen a failed session" —
   and must be decided explicitly (allowed? resumed at which node?).

## Roadmap (agreed direction, not yet ADRs)

- **Phase 2:** (a) interactive manual takeover, and (b) retry/backoff by error class. Each is its own
  ADR, separate from ADR 012.
- **Done:** (c) atomic `state.json` write, with the session lock beside it.
- **After phase 2:** (d) snapshot history + rollback + (e) operator-registered compensation — the
  "industrial" tier, whose cost is measured differently and should be justified by a concrete scenario
  where (a)+(b) are not enough.
