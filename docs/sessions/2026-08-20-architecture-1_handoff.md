# Session note

## Type
architecture

## Goal
Decide whether the interactive node should be able to compute, and if so open the decision as an ADR
rather than as a patch to a frozen one.

## Completion criteria
1. The question is argued in critical mode: at least two alternatives, the trade-off named, the cost
   stated.
2. If it is worth deciding, ADR 015 exists as `Draft` with its registry row, scoped to what the
   evidence supports rather than to everything the idea could cover.
3. ADR 013 is not reopened.

## Scope boundaries
- No code. No implementation branch.
- ADR 013 stays Accepted and unedited: this is the specialization its alternative C reserved.
- Prompt templating is not decided here, only named as the thing pre-processing competes with.

## Status
completed

## Result
ADR 015 "Computation inside an interactive node" is open as `Draft` on `development`, registered, with
six open points to settle before it leaves Draft.

The scope was cut to the half that has evidence: a registered function that runs **after** an answer is
accepted, before the answer becomes the node output. Preparing the question by running a function
first is deliberately excluded for now.

## Decisions
1. **The diagnosis is accepted, the framing is not.** ADR 013 did not skip this: its alternative C
   rejected an answer typed by the action class "as the primary mechanism, possible later as a
   specialization". What changed is the evidence — two workarounds appeared within a week of shipping
   it, both because the interactive node is the only node in the engine that cannot compute:
   `echo_value` in front of a guard to make a declared value routable, and `CHECK`+`COLLECT` around a
   question to accumulate and count.
2. **Post-processing is in scope, pre-processing is not.** Pre competes with prompt templating for the
   same job — assembling the question text from state — and it collides with ADR 013 §6, because a
   question is re-presented on a plain `resume` and a pre-function would make re-presenting execute
   code. Deciding it before templating would build the workaround for a gap about to be closed.
3. **The boundary is data of the exchange, not steps of the process.** Work that deserves its own line
   in the journal stays a node. The verbose form has guard records, counters and a route around a
   failure; a function hidden inside `ask` has none of the three. That is the real trade-off — graph
   verbosity against process visibility — and it is why the ADR states the boundary before the
   mechanism.
4. **The answer is injected, not referenced.** At post-processing time the answered values are not on
   the bus yet: the engine applies a node's writes when the step is taken. So a `param.<name>`
   reference in the function's configuration would read the previous value. The bound answer is passed
   the way `state` and `action_output` already are.
5. **Four alternatives recorded as rejected**: keeping the graph as the only place to compute (kept as
   the rule above the boundary), declarative micro-transforms in the answer declaration (worth
   revisiting as sugar), an external interactive action (the extension point exists, but normalizing a
   model's answer is not team-specific), a node-level pre/post concept for every action (dissolves
   ADR 002), and folding it into ADR 014 (an operator's answer needs normalizing too, and the `FQ` loop
   has no model in it).

## Open questions
The six open points of the ADR, of which two are the load-bearing ones: whether the shape is a second
interactive action or optional keys on `ask` — both have a precedent in this core — and whether a post
function may change an answered value or only add to it, which decides whether the answer declaration
is a contract about what was supplied or about what was stored.

## Next steps
1. Build the ADR-0083 scenario as a real flow (the first goal of phase 2). ADR 015 should not leave
   Draft before it exists, so the shape is chosen against a written flow rather than an imagined one.
2. Settle the prompt templating question, which unblocks reconsidering pre-processing.
3. The per-node visit cap, raised in the same discussion and still unrecorded: ADR-0083 enforces
   `max_visits` per node with its own error code, while this engine counts `visit_counters` and neither
   reads nor enforces them. The coverage note's row claiming that mechanism is "full" is wrong.

## References
- ADR opened: `docs/adr/adr-015-computation-inside-an-interactive-node.md`
- Depends on: ADR 013 (Accepted), ADR 002, ADR 005, ADR 009
- Previous session: `2026-08-19-implementation-15_handoff.md`
- Branch: `development`
