# ADR 017: Per-node visit cap

## Status
Implementing

## Active branch
`feature/adr_017-per-node-visit-cap`

## Context

The engine bounds repetition at two levels today. Within one visit, `max_attempts` — a node
configuration field, default 3 — bounds return-to-self transitions and fails the workflow under
`max_attempts_exceeded`. Across the whole run, ADR 010 gives the session a soft limit and the host a
hard cap (`hard_max_nodes_visited`, default 1000). Between the two there is a gap: `visit_counters`
are written on every departure from a node and read by nobody, so nothing bounds how many times a run
may re-enter *one node*.

The ADR-0083 flow turned the gap into evidence (session `2026-08-20-investigation-1`). The check that
catches a bad answer sits one node after the question, so the retry re-enters the `ask` node as a
fresh visit and `attempt_counters` — reset on every departure — never count up. The flow's own test
gives the same wrong answer five times, unbounded; driven by a live agent, the loop is bounded only
by the global hard cap, which means up to a thousand paid question-answer rounds ending in a
`workflow_paused_safety_limit` reported far from the culprit node. The investigation brief had
pre-declared the test: wanting the cap would be evidence. The flow wants it. The external ADR-0083
engine, where this project started, enforces `max_visits` per node with its own error code.

One boundary was argued before the mechanism was chosen, because it decides the shape. **A business
bound is not a safety bound.** How many follow-up questions a task needs is dynamic — decided at the
question from context, three for one case, more for another — and it is already expressible in flow
data: the bound value is a parameter (set by an answer, a function or an input), guards resolve
`param.` references in their configuration, and with ADR 015 the asking node itself accumulates and
routes on "enough". A safety cap is the opposite: a declared static ceiling that holds precisely when
that dynamic logic is wrong. Making the ceiling dynamic would let broken logic raise its own bound —
the same argument the cap-scoping note records against a workflow raising the host cap.

Constraints:
- ADR 013 §6: a plain `resume` re-presents a question consuming neither an attempt nor a visit; the
  cap must not be touched by re-presenting.
- ADR 010 stays as it is: the host cap protects the machine from any definition; this decision is
  additive and supersedes nothing.

## Decision

### 1. A node may declare `max_visits`, and the engine enforces it on entry

A new node configuration key beside `max_attempts`. When the engine is about to run a node whose
completed visits have reached its declared `max_visits`, the workflow fails under
`max_visits_exceeded`, naming the node — before the action runs, so a question beyond the cap is
never asked and the spend stops before it happens, not after.

### 2. No default

A node without `max_visits` is unbounded, as today, and the ADR 010 caps remain its only backstop.
Any default that fits an interactive retry loop (tens) is false for a recursive scan, whose loop
nodes legitimately complete hundreds of visits; a safety default that half the flows must silence as
routine is worse than an opt-in, because silencing becomes a habit exactly where the cap matters.

### 3. The failure is a workflow failure, not a routable one

`max_visits_exceeded` behaves like `max_attempts_exceeded`: a failure with its own code, not a node
error the capped node's transitions route. The mechanics agree with the symmetry: the entry check
precedes the action, so there is no output for guards to evaluate. The attractive alternative — an
in-graph fork offering continue / summarize / finish on exhaustion — is the budget-checkpoint family
(ADR 010 territory, coverage note friction 2) and is deliberately not smuggled in here.

### 4. The journal gains ordinals; the counters keep their semantics

`attempt_counters` keep resetting on departure — the reset is what makes `max_attempts` a per-visit
bound, and a lifetime bound would trip falsely on legitimate loops. The audit record moves where it
belongs instead: `interactive_answered` gains the **visit number and the attempt ordinal within the
visit**, so each answer event is self-describing — "attempt 2 of visit 3" — rather than
reconstructible by counting events between visit boundaries. This settles the cost recorded in
ADR 015's Consequences: the counters are enforcement state, the journal is the audit surface, and
the retries a post function bounds now leave a direct record.

### 5. The rule for authors, stated so review can hold it

Loop control lives in flow data: the number that means "enough" is a parameter or a condition, owned
by the flow. `max_visits` is the seatbelt above it — declared an order beyond the expected dynamic
bound (a loop designed for up to ten follow-ups declares, say, thirty), reached only when "enough"
never comes.

## Alternatives considered

### A. The global cap is the bound
The status quo. Rejected by the evidence: a live agent pays for up to a thousand rounds before the
stop, and the stop reports at whatever node the budget died on, far from the loop that ate it.

### B. Bound the loop in the graph with existing components
An own counter or collection, a guard comparing against a parameter — expressible today, and with
ADR 015 inside the asking node itself. Kept as **the** mechanism for business bounds, which are
dynamic and belong to the flow. Rejected as the safety answer: it protects only the author who
remembered, and the loop that needs the cap most is the one the author did not foresee.

### C. Lifetime `max_attempts`
Stop resetting the attempt counters, so `max_attempts` bounds the node across visits. Rejected: a
node legitimately visited ten times with one retry each would trip falsely, and the meaning of an
existing declared key would change retroactively.

### D. A default value for `max_visits`
Rejected with §2: false for scans, and a routinely-silenced safety mechanism is worse than an
opt-in one.

### E. A routable `max_visits_exceeded`
Let the capped node's transitions route the exhaustion to a recovery node. Rejected: the entry check
runs before the action, so there is no output to route on; the symmetric precedent
(`max_attempts_exceeded`) fails the workflow; and the in-graph recovery fork is the
budget-checkpoint decision, not this one.

### F. Counters as parameters
Move the engine's counters onto the bus so an `ask` with a post function can accumulate and check
them flexibly — proposed for workflow universality. Rejected three ways: parameters are writable by
nodes, so a post function could reset its own node's counter and the cap becomes advisory — safety
state must be owned by the engine because it bounds exactly the code that got it wrong; the
semantics do not match — a visit is not a question (a re-present is no visit, a recovery pass is
one), so business logic keyed to `visit_counters` would count an engine artifact; and the
universality it aims at already has a better channel — the bound as a parameter, resolved by guards
and functions (alternative B). Read-only exposure of the engine counters to guards was considered
with it and not taken: no evidence, and an own parameter states the flow's intent where an engine
counter only implies it.

## Consequences

- Enables: a declared ceiling on any loop through a node, held by the engine; an interactive retry
  loop stopped at the culprit node for the price of one config key, instead of at the host cap far
  from it; self-describing answer events.
- Costs: a node key and an error code in the help surface (ADR 009); one check on the engine's entry
  path; two ordinals on `interactive_answered`.
- Additive to ADR 010: the session limit and the host cap stay; the scope question of the global cap
  (host vs workflow vs workflow type) stays open in the cap-scoping note on its own merits.
- Settles: the counters cost carried by ADR 015's Consequences.
- Leaves open: the in-graph exhaustion checkpoint (ADR 010 family), and read-only counter exposure
  to guards (no evidence).

## Related ADRs

- Depends on: ADR 002 (node configuration and the failure model), ADR 006 (the journal the ordinals
  land in), ADR 010 (the cap family this joins additively), ADR 013 (the interactive loop that is
  the evidence, and §6 which the cap must not disturb).
- Touches: ADR 015 (its Consequences cost line is settled here), ADR 009 (help surface for the key
  and the code).
- Supersedes: nothing.

## Implementation notes

No POC; the counter half of the mechanism already exists. The entry check reads
`visit_counters` — maintained at every departure — in `_start_engine` before the action dispatch;
the error constant sits beside `ATTEMPTS_EXCEEDED_ERROR`; the ordinals are read from
`visit_counters`/`attempt_counters` when the answer event is recorded. The scenario flow's
unbounded-retry test (`tests/test_adr0083_scenario.py`) becomes the bounded case: the same wrong
answer five times must end in `max_visits_exceeded` at the question node. The key applies to any
node, automatic or interactive — nothing in it is specific to `ask`; the evidence merely came from
an interactive loop.

No open points: the decision is small enough to implement directly once its turn comes.

## Change log

- 2026-08-20: opened as Draft in session `2026-08-20-architecture-4`, from the unbounded retry the
  ADR-0083 flow demonstrated and the counters cost ADR 015 recorded. The business/safety boundary
  was argued first and fixed the shape: dynamic bounds are flow data, the cap is declared and
  static, with no default and no routing. Counters-as-parameters was proposed for universality and
  rejected (alternative F) — universality comes from the bound being a parameter, not from exposing
  engine state to user code.
