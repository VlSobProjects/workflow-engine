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
seven open points to settle before it leaves Draft.

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
4. **The answer takes the slot a registered function already has.** At post-processing time the
   answered values are not on the bus yet — the engine applies a node's writes when the step is taken —
   so a `param.<name>` reference in the function's configuration would read the previous value. The
   first draft invented a new injected parameter for it; that was unnecessary. A registered function
   already receives `output`, which for an automatic node is the previous node's `ActionNodeOutput`, so
   a post function takes the same slot with the output built from the answer. Same shape, different
   source. Two things that were folklore are now written down: the slot holds the object for a
   function and the text for a guard, and the answered values sit in `param_writes`.
5. **The injection convention is extracted, the hierarchy is not touched.** It is written three times
   today — identically in `ActionWithFunction._execute` and `StopAction._execute`, differently in
   `FunctionGuard._check` — and the post stage would be the fourth copy. One function states it, every
   caller uses it. The considered alternative was to give the interactive side the automatic machinery
   by inheritance; rejected because `ActionWithFunction` *is* an automatic action and the engine
   dispatches on `isinstance(BaseAutomaticAction)`, checked first, so such a class would be executed
   instead of presenting, and `execution_mode()` would answer according to the order of its bases. The
   reuse at stake is four lines. Recorded as alternative F so the next reader does not retry it.
6. **Moving the engine's dispatch to `execution_mode()` is an independent cleanup.** The enum exists
   for exactly this distinction and is used only by the help contract today. Because the hierarchy
   stays as it is, this ADR does not need it.
7. **Six alternatives recorded as rejected**: keeping the graph as the only place to compute (kept as
   the rule above the boundary), declarative micro-transforms in the answer declaration (worth
   revisiting as sugar), an external interactive action (the extension point exists, but normalizing a
   model's answer is not team-specific), a node-level pre/post concept for every action (dissolves
   ADR 002), folding it into ADR 014 (an operator's answer needs normalizing too, and the `FQ` loop has
   no model in it), and giving the interactive side the automatic machinery by inheritance (decision 5).

## Open questions
The seven open points of the ADR, of which two are the load-bearing ones: whether the shape is a second
interactive action or optional keys on `ask` — both have a precedent in this core — and whether a post
function may change an answered value or only add to it, which decides whether the answer declaration
is a contract about what was supplied or about what was stored.

## Next steps

The next session is an **investigation**: it gathers the evidence ADR 015 needs and changes no engine
code. ADR 015 must not leave Draft before it, and the prompt templating question must not be decided
before it either — both are waiting on the same material. The brief is below, in the order the work
takes.

### What the investigation has to produce

Answers, with evidence, to open points 1, 2, 3 and 7 of ADR 015, plus the node count that the
templating decision needs. Everything else in the ADR can be settled by argument; these four cannot.

### 1. Write the ADR-0083 flow with today's core, and run it

One flow covering `Q`, `A`, `I`, `FQ`, `STOP`, the counters, the `validators` and the error catalogue.
`S` stays out: it waits for the trust decision about a process-running function. Run it twice — once
by a scripted end-to-end pass, once driven by a live agent, because the second is what the whole
question is about.

Record while writing, not afterwards:

- the total node count, and of those, every node that exists **only to adjust data**: surfacing a
  value into an output text, composing a sentence, appending to a collection;
- every place where the answer had to be constrained by prompt wording ("answer exactly `approved`")
  instead of by code, because that is the disguised form of the same gap;
- every place where a reference had to be shown as a bare value because it could not be written inside
  a sentence — this count, and nothing else, is what the templating decision needs.

Where the flow lives is the first thing to decide: a conformance scenario under `tests/`, which is
what it actually is, or a fourth template in `examples/`, which makes it operator-facing and therefore
shorter and less complete. The recommendation is `tests/`.

### 2. Rewrite the same flow on paper in both candidate shapes

Not code: the same nodes as they would read with a post function, once as a separate `ask_function`
action and once as optional keys on `ask`. Compare three things: how many nodes disappear, how the
node reads at the point where the function is attached, and what the journal loses in each case
(a vanished node takes its guard record, its counters and its route-around with it).

→ decides open point 1 (shape).

### 3. Classify every post use the flow produced

Sort each one into: normalizing a declared value; producing the text a guard routes on; accumulating;
producing an artifact; combining the answer with other state.

→ decides open points 2, 3 and 7 together, because the classification is the argument. If the real
uses only ever *add* — a routing text, an append — then a post function can be forbidden from changing
an answered value and the audit story stays simple. If normalizing a declared value is the common
case, it has to be allowed, and the ADR has to say what `interactive_answered` then means: the name
was answered, but not necessarily with the value that was stored.

### 4. Two questions to answer by reading the code, not by building

- **Where the hook sits.** Confirm against `_start_engine` that a post stage between accepting the
  answer and selecting the transition introduces no ordering surprise — in particular that it runs
  before `_proceed_with_output` and that its output is the one `state.update` applies.
- **What a failure does to an already-journaled answer** (open point 4). The precedent to read is what
  a failing node does today to a journaled `inputs_set`: the binding happened, the run then failed, and
  the journal keeps both. If that is the accepted shape, `interactive_answered` followed by a node
  failure needs no new rule.

### Out of scope for that session

No engine changes, no ADR status change, no `S` function. The per-node visit cap is only opened if the
live run actually needs it: the global hard cap already prevents a runaway, so wanting it is evidence,
and not wanting it is evidence too.

### Small correction to take first

The coverage note's row claiming `attempt_counters` / `max_visits` are carried "full" is wrong:
ADR-0083 enforces `max_visits` per node with its own error code, while this engine counts
`visit_counters` and neither reads nor enforces them — the field is not even on `StateReadOnlyView`.
That note is the yardstick the investigation measures against, so the row is fixed before it starts.

### After the investigation

1. Settle ADR 015 open points 1, 2, 3 and 7 in the ADR text, then decide whether it leaves Draft.
2. Decide prompt templating with the count from step 1, which also unblocks reconsidering
   pre-processing (ADR 015 open point 6).

## References
- ADR opened: `docs/adr/adr-015-computation-inside-an-interactive-node.md`
- Depends on: ADR 013 (Accepted), ADR 002, ADR 005, ADR 009
- Previous session: `2026-08-19-implementation-15_handoff.md`
- Branch: `development`
