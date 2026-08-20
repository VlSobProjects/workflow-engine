# How an answerer that comes back gets the context, and what the read commands show

- **Date:** 2026-08-20
- **Trigger:** discussion during the implementation session that folds the data-only nodes of the
  ADR-0083 scenario (`2026-08-20-implementation-5`). The question raised was what happens when an
  agent walks away from an interview in the middle, and how it later picks the interview up with the
  previous questions and answers in hand.
- **Status:** promoted → ADR 018
- **Affected:** ADR 006 (journal), ADR 009 (CLI contract), ADR 013 (interactive exchange), ADR 018 (session read surfaces — the promotion)

An interrupted interview costs nothing today: the session stays paused, `resume` without an answer
re-presents the same question and consumes neither an attempt nor a visit (ADR 013 §6), and a
question waiting for an answer is not engine work, so the ADR 010 node budget does not bound how long
it stays open. Nothing expires. What is missing is not a way back in — it is what the one who comes
back can read.

## What can be read today

`show-state --session-id <id> --json` carries the whole persisted state in one document:
`parameters` with their real values, `outputs`, `errors`, the artifacts, the current node and the
budget. So the accumulated answers of a flow that collects them — the `qa_log` pattern of the
ADR-0083 scenario — are already readable by whoever answers next.

## What cannot

1. **The journal and the guard traces are not in the contract.** `session_events` and `guard_results`
   are persisted in `state.json` and never leave it: no command publishes them. They are the half that
   answers "why did this fail" — which guard answered what on which node, who answered when, under
   which code the node failed, how many visits and attempts there were. Today that means opening the
   state file by hand.
2. **Reading is all-or-nothing.** `show-state` returns everything. An agent with a bounded context
   pays for the whole bus to read one accumulated list, and a human reading a failure scrolls past
   every parameter to reach the error.
3. **The engine keeps no record of the exchange itself.** Neither the text of the question that was
   published nor the text of the answer is stored: the journal records names and codecs and never
   values (ADR 013 §9), and the only values that survive are the ones the author declared in `answer`
   or kept with `save_as`. A transcript of the interview therefore exists only where the flow author
   built one. The engine cannot hand a returning answerer "everything that was asked and answered",
   because it never had it.

## Why the context is pulled, not pushed

The neighbouring shape — putting the prior exchange inside the published question — is already
rejected three times over in `2026-08-20-question-rendering-for-an-audience.md`: the block is a
disclosure boundary, and state embedded in it shows every answerer the whole bus, machine paths
included; a plain `resume` must not run code whose effects the engine cannot check; and a question
built from state the block does not carry is not reconstructible from the run's record.

A read command is a different door and none of those reasons reaches it. The answerer asks the engine
for what it needs, through a surface with its own audience and its own boundary, instead of the
engine deciding what to show inside a question. This note does not reopen the rejected shape; it
records the other door.

## The proposed shape

The operator's position, taken during the discussion above and recorded here as the leading option:

- **`show-state` shows the state of the run, and nothing else.** No parameters. What belongs there is
  what a caller needs to know about the run as a run: where it stands, what failed, what it has been
  doing.
- **Parameters get their own two commands**: one listing the names with their types, one returning the
  value of a named parameter. Two commands rather than one with a selector, because each then has a
  single shape of result — a list, or one value — rather than a `data` block that changes shape with a
  flag.
- **The journal is treated the same way.** Moving it into `show-state` whole would move the problem
  rather than solve it: a long run has many events, and the output becomes as unreadable as the
  parameter dump it replaces. It wants its own surface with a bound — a tail, or a filter by event
  code or by node. The guard traces are bounded by construction (`guard_results` keeps the latest
  attempt per node) and can sit with the status.
- **`outputs` is a candidate for the same treatment**, and is left open here.

## What the session that takes this on has to decide

1. **Removing `parameters` from `show-state` is a removal, not an addition.** The field is documented
   in `README.md` and is part of the command result today, and every CLI extension so far — `data.export`,
   for instance — was additive and therefore needed no ADR. This one changes what a caller already gets.
   Decided during the discussion: it is done now, while the project is private, and it is done under an
   ADR of its own, which also carries the read commands it splits into.
2. **What actually stays in `show-state`.** Status, last event, errors, counters, budget, current node,
   and probably the artifacts and deliverables a caller needs to fetch a result — the boundary is the
   decision, not a detail.
3. **How a value is rendered.** `render_value_as_text` already fixes the rule for text — POSIX for a
   path, compact JSON for a collection — but a machine reader may want the codec envelope the state
   itself is written in. One or both, and which one `--json` carries.
4. **What a name that does not exist is.** By the existing exit code layout that is `4`, a
   command-level resolution error, not an empty success.
5. **Whether the transcript question is answered by this at all.** Reading parameters gives back what
   the flow accumulated, which is the pattern that already works. It does not give back the questions
   themselves. If a returning agent must see the exchange rather than its results, one of two stances
   has to change: either the flow author keeps composing the record as data, or the engine starts
   keeping the exchange — which contradicts the journal's stance that it stores no values. Nothing in
   the ADR-0083 scenario forces the second yet.
