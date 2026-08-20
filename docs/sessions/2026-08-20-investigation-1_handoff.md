# Session note

## Type
investigation

## Goal
Gather the evidence ADR 015 needs by building and running the ADR-0083 flow with today's core, so that
open points 1, 2, 3 and 7 are answered from a written flow rather than from an imagined one.

## Completion criteria
1. The ADR-0083 flow exists as a conformance scenario under `tests/`, covering `Q`, `A`, `I`, `FQ`,
   `STOP`, the counters, the `validators` and the error catalogue, and it runs green.
2. It has been run twice: once by a scripted end-to-end pass, once driven by a live agent answering
   the published question blocks.
3. The counts are recorded: total nodes, nodes that exist only to adjust data, answers constrained by
   prompt wording instead of by code, and references that had to be shown as a bare value because
   they could not be written inside a sentence.
4. The same flow is rewritten on paper in both candidate shapes, and every post use the flow produced
   is classified.
5. The two code-reading questions are answered: where the post stage sits relative to
   `_proceed_with_output` and `state.update`, and what a node failure does to an already-journaled
   `interactive_answered`.

## Scope boundaries
- No engine code. The only production-side change allowed is none; the flow is a test.
- No ADR status change and no edit to the decision text of ADR 015: settling its open points is the
  next session.
- No `S` node: it waits for the trust decision about a process-running function.
- Prompt templating is not decided here; this session only produces the count it needs.

## Status
completed

## Result

`tests/test_adr0083_scenario.py` is the flow: a release readiness review answered by an agent, eleven
nodes, covering `Q`, `A`, `I`, `FQ`, `STOP`, `auto_log_stop`, the attempt counters, a node `validators`
entry, the error catalogue and a `handoff_ref` deliverable. Six tests, green; the whole suite is 370
passed and `ruff check .` is clean.

It was run twice. The scripted pass is the test file. The live pass was driven answer by answer through
the CLI against a real folder, with the answers composed as a model would compose them rather than as
the flow would like them; it completed and exported a real handoff table. Two of the seven live answers
stalled the run, and both stalls are the evidence below. The flow was extended twice while running it —
a recovery route back to the question, and the `auto_log_stop` route — and the live answers were then
replayed against the final flow to keep the two runs the same flow.

All five completion criteria are met. The correction the brief asked for first is applied: the coverage
note's counters row claimed `max_visits` was carried "full", and `visit_counters` is written per node
and read by nobody, so a loop is bounded by what it collects or by the global hard cap, not per node.

### The counts

Eleven nodes: four `ask`, six `function`, one `stop`.

| Category | Count | Nodes |
| --- | --- | --- |
| Only to adjust data | 4 | `CHECK_ROOT`, `CHECK_ISSUES`, `FQ_CHECK`, `FQ_COLLECT` |
| Preparation of a collection | 1 | `INIT_LOG` — removable only if an `APPEND` write may create |
| The questions themselves | 4 | `ASK_ROOT`, `ASK_INSPECT`, `ASK_FOLLOWUP`, `ASK_APPROVE` |
| The tail | 2 | `HANDOFF`, `FINISH` |

Every one of the four data-only nodes sits directly next to an `ask` node, and not one of them exists
for any reason other than that the `ask` node cannot compute.

Answers constrained by prompt wording instead of by code: **four**, plus one the wording did not think
to constrain — that a path had to be absolute, which is what broke the live run.

References that had to be shown as a bare value because they could not be written inside a sentence:
**three**, one for each question that needed prior state; only the first question, which needs none,
escaped. This is the count the templating decision was waiting for. It comes with a second fact:
a list shown this way reaches the answerer as a Python repr.

### The same flow in both candidate shapes

Both shapes attach a function to **all four** `ask` nodes and reach the same node count.

| | today | with a post function |
| --- | --- | --- |
| nodes | 11 | 7 — 6 if an `APPEND` write may create the collection |
| `CHECK_ROOT` | resolves and checks the answered path | folded into `ASK_ROOT` |
| `CHECK_ISSUES` | surfaces the issue list to route on | folded into `ASK_INSPECT` |
| `FQ_COLLECT` | appends the pair | folded into `ASK_FOLLOWUP` |
| `FQ_CHECK` | reads the collection size after the write landed | folded into `ASK_FOLLOWUP` — the function computes the size from what it already holds, not from a guard seeing its own write |

The node count does not separate the two shapes. What separates them is that a flow made of questions
uses `ask_function` four times and plain `ask` zero times, so a separate action makes the plain form the
exception an author never picks.

What the journal loses is four guard records and four visit counts. The sharper loss is the one the
counters make: a retry bounded by `max_attempts` leaves **no count at all** behind it, because
`attempt_counters` is reset on every departure from the node. In the live run the node that retried
ends at zero attempts and one visit; only the two `interactive_answered` events say it happened twice.

### Classification of every post use the flow produced

| Class | Count | Where |
| --- | --- | --- |
| Normalizing a declared value | 2 | resolving the answered path; normalizing the decision word |
| Producing the text a guard routes on | 2 | the issue count; the loop size |
| Accumulating | 1 | appending the question/answer pair |
| Producing an artifact | 1 | the report paragraph — wanted, and not expressible today by either route |
| Combining the answer with other state | 0 | not needed by this flow |

## Decisions

Evidence, not decisions: ADR 015 is not edited here. What the evidence supports, per open point:

1. **Shape — optional keys on `ask`.** All four questions want a function, so a second interactive
   action would leave the plain one unused in a flow that is entirely questions. The `stop` precedent
   (a function only when one is configured) fits what was observed; the `ActionWithFunction` precedent
   does not.
2. **A post function must be allowed to change an answered value.** Normalizing is not the rare case:
   it is two of the five uses, and it is the half that stalled the live run twice. The consequence has
   to be written into the ADR — `interactive_answered` then means the name was answered, not that the
   stored value is what was supplied.
3. **Write modes: `APPEND` must be allowed from the function.** Accumulating is a real use and the
   restriction of ADR 013 alternative H belongs on the answer document, not on the node.
4. **An answer whose node then fails already lands on the bus, and this is not new.** The engine applies
   the node's writes before it looks at whether the step failed, so a success answer routed straight
   into a `fail` target leaves both the `interactive_answered` event and its values behind. `save_as` is
   the one thing skipped, because the output then carries an error code. Proven by a test, not only by
   reading. So a failing post function needs no new rule: it is the shape the engine already has.
7. **`output` alone carries every use this flow produced, and `Answer` is not justified by it.** The
   decisive case is the decision node, which declares no values at all — the decision is in the answer
   text, so `param_writes` alone could not serve it and the output object could. Nothing in the flow
   needed the actor, the status or the message. The ergonomic complaint stands: two of the five uses
   read a declared value, and reading it means `output.param_writes[name].value`.

Two findings that belong to ADR 015 without being on its list:

- **Where the hook sits is not where it looks.** Placing it in `start_workflow`, between `bind_answer`
  and `_start_engine`, would run it before `_set_parameters` applies the node's own `set_parameters`
  block and before the state view is built, so a function referencing such a parameter would read the
  previous value. The hook belongs **inside** `_start_engine`, after `_set_parameters` and the state
  view and before `_proceed_with_output`. Placed there, the same variable is what the guards see and
  what `state.update` applies, so there is no second ordering question.
- **`save_as` changes meaning on a node that gains a post function**, because it stores the node's
  output text, which is then the function's text and no longer the answer's.

## Open questions

- **A per-node visit cap now has its evidence.** The check that catches a bad answer sits one node
  later, so the retry re-enters the question as a fresh visit and `max_attempts` never counts up. The
  flow's own test gives the same wrong answer five times unbounded. The brief said wanting the cap
  would be evidence; the flow wants it. It belongs with `2026-08-19-hard-node-cap-scoping.md`, not with
  ADR 015.
- **A re-presented question tells the answerer nothing.** Both live stalls returned the identical
  question block with an empty `errors` map. ADR 013 §6 defines what re-presenting *costs* and not what
  it *says*. A post function bounds the loop but does not answer this.
- **If ADR 015 lands, the attempt counters stop recording the retries** it makes possible, because they
  reset on departure. Either they should not reset, or `interactive_answered` should carry the attempt.
- **A declared `Path` is published as `pathlib._local.Path`** in the caller-facing question block. The
  Python-version-dependent codec name of `2026-08-18-adr012-deferred-questions.md`, now on the published
  surface rather than only in the state.
- **A `dict` answer has no key schema**, so the columns of the exported deliverable rest on a sentence
  in the instruction. Not an ADR 015 question; a declaration-shape question (ADR 012).

## Next steps

1. Settle ADR 015 open points 1, 2, 3, 4 and 7 in the ADR text from the evidence above, add the
   placement finding and the `save_as` consequence to §3, then decide whether it leaves Draft.
2. Decide prompt templating with the count of three, which also unblocks reconsidering pre-processing
   (ADR 015 open point 6). The rendering of a non-string value inside a sentence is part of that
   decision, not separate from it.
3. Take the per-node visit cap to `2026-08-19-hard-node-cap-scoping.md` and decide it there.
4. Decide separately what a re-presented question tells its answerer; it is an ADR 013 §6 question and
   ADR 015 does not close it.

## References
- Branch: `test/adr0083-scenario-flow`
- Added: `tests/test_adr0083_scenario.py`
- Updated: `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`
- Evidence for: ADR 015 (Draft), open points 1, 2, 3, 4 and 7
- Related: ADR 013 (§6), ADR 010, ADR 012, ADR 014
- Previous session: `2026-08-20-architecture-1_handoff.md`
