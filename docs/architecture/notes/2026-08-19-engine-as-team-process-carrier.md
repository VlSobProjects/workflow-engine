# The engine as the carrier of a team's development process

- **Date:** 2026-08-19
- **Trigger:** a theoretical scenario raised after the ADR 013 review: a project developed by people
  together with AI agents, where a new participant receives a set of workflows — the team's rules
  already expressed as functions and nodes — and both the human and the agent simply walk the graph,
  spending attention only on what actually needs it, while the process itself forgets nothing
- **Status:** open
- **Affected:** ADR 002 (one node at a time, guarded transitions), ADR 003 and ADR 004 (storage as the
  extension point), ADR 005 (component delivery), ADR 006 (the bus and the journal), ADR 010 (budget),
  ADR 013 (Accepted; the interactive exchange this scenario rests on)

This note exists because the scenario is the natural end point of the project, and because the work it
needs is already scattered across six other notes. It is a collection point, not a decision. Where the
project owner has taken a position, it is recorded as a position, not as a settled question.

**Correction (`2026-08-23-architecture-1` §1, recorded at triage):** this note is a later application
of the engine, not the purpose `docs/architecture/purpose.md` states and measures the architecture
against. Kept open as the direction this scenario is a step towards; nothing here is phase-2 scheduled
work.

## What it replaces

The project owner's formulation, kept verbatim because it states the goal better than any description
of the mechanism does:

> Instead of prompts, links, promises and reminders — a stream of instructions, a deterministic check
> before the checkpoints, a fully recoverable state to continue the work from, delivery of a ready
> process instead of instructions on how and what to do.

This is the sentence to judge the direction by. It also sets the priority between the two scenarios
this project is chasing: the questionnaire coverage
(`2026-08-19-adr0083-coverage.md`) is the near goal, the one that has to be *run* and
checked; this note is the direction that goal is a step towards, and nothing here is scheduled work.

## Why the scenario fits this engine at all

Not everything a process needs is missing. What the engine already carries:

- **Order that cannot be skipped.** A node is not passed until its guards and `validators` hold, and a
  failure goes to a declared error code rather than to goodwill.
- **One contract whoever answers.** ADR 013 §1: the `ask` node does not know whether a human or an
  agent is on the other side. The scenario's "both walk the same nodes" is the delivered design, not
  an adaptation of it.
- **A pause that costs nothing to hold.** The run lives in `state.json` between turns, for minutes or
  for days, with no process waiting.
- **An audit trail that answers "how did we get here".** `session_events`, `guard_results`, `outputs`,
  and parameters carrying the node that produced them. For "the process is provable" this matters more
  than the graph itself.
- **A definition frozen per run.** `init-new-session` copies the workflow into the session's storage,
  so the team can publish a new version of the rules without breaking the runs already in flight.

## The tensions, and where the project stands on each

### 1. Concurrency — two different problems under one word

Worth separating, because their costs differ by an order of magnitude.

**(a) Concurrent access to one session.** `JsonStorage.save_state` opens the file for writing and
overwrites it: no lock, no atomic replace (the same gap as the open `state.json` write item of the
recovery note). The engine is a single writer by construction. Two participants resuming one session
lose each other's writes. Cost to close: a `Storage` implementation with locking or optimistic
concurrency — the extension point ADR 003 and ADR 004 deliberately left, so no new concept is needed,
only a real store and a decision about what a conflict means.

**(b) Parallel nodes inside one run.** A different matter entirely: the engine walks one node at a
time, and the bus has no notion of a fork, a join, or two writers of one parameter. This touches
ADR 002 and ADR 006 at their core — what a transition target means when there are several, what
happens to `attempt_counters` and the ADR 010 budget in a branch, and which write wins when branches
rejoin.

Position of the project owner: parallel nodes would pay off in speed even for the phase 1 scenarios
already built, and the decision is between phase 2 and phase 3; taking it on pulls in everything else
plus a body of concurrency management, so it is deliberately approached with caution. A relational (or
not) database enters through (a), not through (b): a store is what makes concurrent access safe, while
parallelism is a graph semantics question that a database does not answer.

Reading it back: (a) is a storage decision, and (b) is a language decision. They can be taken in
either order, but taking (b) first without (a) produces a graph that can fan out and a state that
cannot hold the result.

### 2. Delivery, and the missing capability contract

A workflow references functions by name and declares nothing about which components provide them. A
participant needs the engine, the component package, and the `external_modules` entry before the file
means anything, and the wheel has no delivery channel yet (see the installation and distribution
note).

Position of the project owner: this is not a core problem. The core is the core; the external adapters
ship with the workplace, and a team's unique components can perfectly well live in a database and be
loaded from there. The question is deliberately parked until publication.

What still stands under that position: the guarantee becomes the workplace's, not the workflow's. That
is a coherent stance — it just has to be stated somewhere, because a workflow handed to a participant
whose workplace lacks a component fails at build time with a component name and no idea what to
install. A one-line manifest inside the workflow ("this flow needs these components") is not the only
answer, but something has to answer it.

### 3. Identity, logging and security as a layer

Position of the project owner: this needs a logging and security layer, and it should not be painful —
the architecture already lets much of the source identification be assembled automatically.

Largely true, with one boundary that the layer cannot cross. The engine can attribute everything that
passes through it, and after the write-provenance fix it does. What it can never do is verify a claim
that arrives inside an answer document: `"actor": "tech-lead"` is text the caller wrote. Authentication
therefore belongs to the transport — the agent process, the web front end, whatever holds the session —
and the journal has to record what the transport asserted rather than what the answer claimed. That is
a constraint on *where* the layer sits, not on whether it is expensive. It also interacts with §5: if
the agent is the human's interface, the agent is the thing asserting on the human's behalf.

### 4. Irreversible steps

Position of the project owner: the contract covers it — the user's function pushes, and the same
user's function rolls the state back when needed.

Consistent with the engine's stance that an error is a value, not an exception. The gap is not the
capability but the declaration: nothing in a node says "this step is irreversible, and this is its
compensation". Today the pattern is expressible by hand — route the failure to a compensating node
with an `errors` transition — and nothing more is needed to start. Making it a contract (a declared
compensation per node, run by the engine on the failure path) is the part the recovery note keeps
open, and it only becomes urgent when the graph fans out, because then the failing branch is not the
only one that has already acted.

### 5. The human interface

Position of the project owner: two routes, and they are not exclusive — everything through the agent,
which then gives the human a text interface of its own; or a web surface later.

The first route is what ADR 013 was designed for: the agent is the interface, the engine is the state.
It needs nothing new. The second is the same contract over a different transport, which is
alternative D of ADR 013, deliberately deferred and explicitly described there as something that would
wrap the CLI/JSON contract rather than replace it.

## On "that is CI's job"

The first framing in the discussion was that running ruff, tests and pushes is continuous
integration's work and that a node doing it is a worse CI: sequential, uncached, and run only because
somebody reached that node.

That framing was too binary, and the counter-argument is the stronger one. A pipeline is expensive and
late: it runs after the push, its failure costs a round trip, and on a large project the interesting
failures are the ones a cheap local check would have caught before the push ever happened. A node that
runs the cheap local validation, in a fixed order, before the step that pushes, is not a duplicate of
the pipeline — it is the gate in front of it, and it is exactly the thing that is easy to forget by
hand.

So the split is not "checks belong to CI, decisions belong to the engine". It is:

- **the engine** owns the local, ordered, non-forgettable pre-flight and everything that needs a
  judgment, an agent's action, or a branch on an answer;
- **the pipeline** owns what only it can do — the matrix of environments, parallelism, caching, the
  shared history, and the enforcement that survives a participant who never ran the workflow at all;
- and the pipeline is reachable *from* the graph like anything else: a node that triggers it and a
  node that waits for its verdict are ordinary nodes.

What remains of the original caution is narrow: do not rebuild the matrix, the cache and the
parallel fan-out inside the graph. Run the cheap check locally, and call the pipeline when the
pipeline is what is needed.

## What this scenario would actually require, in order

Nothing here is new work invented by this note; each item is already open somewhere. The order is the
one the scenario imposes, not the one the notes were written in.

1. **Concurrent access to a session** (§1a) — without it a team process is a set of private runs, which
   may well be the right first answer.
2. **Identity at the transport boundary** (§3) — the moment a process approves and pushes, an
   unverified label stops being an audit trail.
3. **Delivery of components with the workplace** (§2) — parked until publication by decision, but it is
   what makes "hand a colleague the workflows" a real sentence.
4. **Text interpolation** — every question to a human currently shows a bare resolved reference instead
   of a sentence; the shipped `ask` example demonstrates the cost. Decided: ADR 016 (Draft, session
   `2026-08-20-architecture-3`).
5. **A process-running function and its trust boundary** — the same decision the ADR-0083 coverage note
   records for its `S` node type.
6. **Declared compensation** (§4) — after the graph can fan out, not before.
7. **Parallel nodes** (§1b) — the largest of them, and the one with no partial version.

## Related notes

This note collects; the detail stays where it is.

- `2026-08-18-recovery-and-resilience-roadmap.md` — atomic state write, retry, rollback, compensation
- `2026-08-19-interactive-exchange-publishing-boundary.md` — the actor/identity policy, the published
  contract and its versioning
- `2026-08-19-installation-and-distribution.md` — how an operator obtains the command at all
- `2026-08-19-entry-point-discovery.md` — how components register when they come from outside
- `2026-08-18-adr012-deferred-questions.md` — reference resolution and the input transport
- `2026-08-19-adr0083-coverage.md` — the questionnaire scenarios this engine can already carry
