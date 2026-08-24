# ADR 021: The node-record channel

## Status
Implementing

## Active branch
`feature/adr_021-node-record-channel`

## Context

The purpose document promises that a run can be explained: the path is chosen by the data and
explained by the journal, and every model answer is recorded. The phase 2 exit scenario repeats the
promise as its criterion. The code does not keep it yet, as investigation
`2026-08-24-investigation-1` measured:

1. Node execution is not journaled. `state.session_events` holds lifecycle events only — created,
   started, inputs set, answered, resumed, paused, completed, failed, exported. A node that ran
   leaves no row.
2. The per-node slots of the state — output text, error, guard results, counters — hold the latest
   visit and are overwritten by the next one. In a loop, which is how the shipped
   `folder-inventory-to-csv` walks a tree and how the ADR 014 `chunked` variant will call a model
   per chunk, the history of every earlier visit survives nowhere.
3. An action cannot write a trail. It receives a read-only state view and returns one output the
   engine applies; a write from inside the action would record effects the engine never applied.
4. The journal is serialized inside `state.json`, which is rewritten whole several times per node.
   Lifecycle events are few, so today that is safe; a record per visit changes the regime — the
   list grows with the run and the whole file is rewritten at every step, and resume parses the
   full history back.

ADR 014 §4 needs a destination for its call audit; deciding the destination after model-call
records already flow into the session journal would mean migrating them, which is why this decision
comes first (roadmap step 8).

Constraints:
- The trail is written by the engine only (ADR 006: the journal belongs to the engine).
- A trail entry carries names and codec names, never values (the ADR 013 §9 rule).
- A session directory is portable; what explains a run travels with it (ADR 003, ADR 008).
- Reads are bounded and explicit (ADR 018).
- Phase 2 is additive; nothing is removed from the state model.

## Consumer

The party that acts on this decision is the reader who explains a finished, failed or abandoned
run after the fact — the operator, a human or an agent, holding only the session directory and the
CLI. The freeze-gate evidence is class 4: `folder-inventory-to-csv`
(`examples/folder-inventory-to-csv.md`), whose queue-driven walk visits its loop nodes once per
tree entry — exactly the history the state slots overwrite today. The gate is a run over a
prepared tree whose walk is read back per node and bounded from the record command, documented in
the walkthrough; the walkthrough and the scenario registry list this ADR in the same session. The
phase consumer is `load-test-triage` (`docs/architecture/scenarios/load-test-triage.md`): "the
path explained by the journal" is its exit criterion, and its judgment steps are the `llm` calls
whose audit (ADR 014 §4) lands in this channel.

## Decision

### 1. Every node visit leaves a record, written by the engine

Recording is automatic and unconditional: it is the engine's promise from the purpose document,
not an author's option or an installation's habit. One record describes one concluded visit — the
action ran (or was refused on entry), the output was applied, and the transition was chosen or the
workflow ended at that node. The engine is the only writer, and it writes after applying the
output and choosing the transition, so a record only ever describes effects that took hold.

The common shape of a record:

- `record_id`, `timestamp` — identity and order, the `SessionEvent` discipline;
- `node_id`, `visit`, `attempt` — where and which time, the ADR 017 ordinals;
- `action` — the registered action name, and the function name where the action is a function
  wrapper;
- `status` — `completed` or `failed`, with the error code when there is one;
- `guards` — the guard evaluations of the visit and the transition that was taken (target node,
  end, or failure code);
- `writes` — the names, codec names and write modes of the applied parameter writes, and the names
  of registered artifacts.

Names and codec names, never values: the ADR 013 §9 journal rule extends to the record stream
unchanged. Values live in the state and in artifacts, where codecs keep their types.

A record carries one open `details` member beside the common shape, filled by the engine per
action kind. The ADR 014 call audit — provider, model, error class, token counts — becomes the
`llm` details of this record when that ADR lands; it defines no second trail.

A visit that pauses (an interactive node waiting for its answer) has not concluded: the pause
stays a journal lifecycle event as today, and the record is written when the answered visit
concludes. A run abandoned mid-pause leaves no record for the pending visit; the journal already
says where it stood.

### 2. The destination: an append-only stream outside the state

Records are appended to a dedicated per-session stream in the session directory, beside
`state.json` — not into the state. The criterion this fixes: **the state holds what a resume
needs; the trail holds what an explanation needs.** Records are not needed for resume by
construction — the overwritten per-node slots already give the engine everything a resume reads —
so they do not belong in the file that resume parses and the engine rewrites whole at every step.

The persistence contract (ADR 003) gains two operations for the stream: append one record, and
read records bounded. In `JsonStorage` the stream is a JSON-lines file; the medium is the storage
implementation's concern, as it is for the state document. The stream is write-only for the engine
during a run — no engine logic reads it back — and append-only for everyone: a record is never
rewritten, which is what makes the trail evidence.

The state file stays what it is; nothing moves out of it. Crash semantics follow from the split:
the state is authoritative, and a trail whose last record is missing after a crash is an
incomplete account of a run whose state is still exact — tolerable in evidence, intolerable in
state. The hard node cap (ADR 010) bounds the number of visits and therefore the stream's size
per session.

### 3. Payload stays in artifacts

The record stream carries names; it never carries payloads. Where a step's payload must survive —
the prompt and reply of a model call, sized in kilobytes — it is written as artifacts under
ADR 011, opted in per node **in the workflow definition** (the ADR 014 §4 `record: true` shape),
so verbosity is versioned with the definition, not configured per machine. The record then names
the artifacts, and the two channels meet by name.

### 4. The read surface: a dedicated command in the ADR 018 pattern

`show-records --session-id <id> [--tail <n>] [--node <node_id>]` publishes the stream as
persisted, in the ADR 018 §3 discipline exactly: whole without flags, `--node` filters first,
`--tail` bounds last, the answer reports how many records it carries next to how many the stream
holds, a `--tail` below `1` is a command error. It joins the info command set: `workflow_status`
reported informationally, exit `0` on command success, `4` on resolution errors.

`show-journal` is untouched: ADR 018 froze it as publishing `session_events` as persisted, and the
two streams answer different questions — the journal says who drove the session, the records say
what the run did. Per-visit facts live in records only; the session journal gains no per-visit
event codes, so nothing is bookkept twice.

## Alternatives considered

### A. The existing session journal
Records as `SessionEvent`s in `state.session_events` — the wording ADR 014 §4 carried. One trail,
one existing read surface, zero new machinery. Rejected: it changes the regime of the state file —
a list growing by one per visit, rewritten whole at every save, several saves per node, parsed
whole on every resume; the `chunked` loop is exactly that regime. Choosing it now schedules the
migration this decision exists to avoid.

### B. A separate record list inside the state
Typed and resume-visible, but it inherits the whole cost of A — the growing state file rewritten
whole — while giving up A's one advantage, the single stream: two trails that must be correlated.
Rejected as strictly weaker than A.

### C. Artifacts as the record channel
Artifacts already persist, export with the deliverables, and ADR 014 already uses them. Rejected
for the records themselves: an artifact is a named deliverable registered in the state (the growth
returns), with no filtered or bounded read — a per-visit record trail would turn the deliverable
registry into a log of generated names. Kept as the payload channel (§3), which is what ADR 011
built it to be.

### D. Opt-in recording via a wrapping or subclassed node
Nothing is recorded unless the author wraps the node with a recording variant. Rejected three
times over: extension travels through registration, not inheritance (the ADR 014 alternative F
argument); an action cannot write the trail without breaking the ADR 006 ownership (context
finding 3); and explainability is the engine's promise — a run of unwrapped nodes would satisfy no
scenario that asks for its path.

### E. Recording everything, switched per component in the engine configuration
The §1 content behind a configuration switch. Rejected: the trail becomes an installation's habit —
two runs of one definition on two machines leave different evidence, the flaw for which ADR 014
rejected its driver alternative. Where verbosity is legitimate it belongs to the definition
(§3 `record: true`), and the volume concern belongs to the destination (§2) and the bounded read
(§4), not to a switch.

### F. The standard `logging` framework, consumed by administrators
Introduce Python `logging` with standard configuration and declare log files the recording. It is
the wrong concern: the trail is a domain artifact — read back by the CLI, correlated with the
journal, portable with the session directory, consumed by machines (a guard routes on an error
class; an audit reads the model name) — while process logging is machine-configured, unordered
relative to state saves, outside the session contract, and by its own framing not for the
application to read, which leaves the channel without the consumer rule 11 demands. Rejected as
this channel; a diagnostic logging facility for the engine itself remains possible as a separate,
later decision.

## Consequences

- Enables: a run whose path is explained from its session directory alone — the phase 2 exit
  criterion; per-visit history that loops no longer erase; the destination the ADR 014 call audit
  needs before it flows; the append-only trail the recovery note's rollback sketch (d) assumes.
- Costs: a record model, two operations on the persistence contract and their `JsonStorage`
  implementation, one new info command, and one more file in the session directory.
- Closes off: values in records (names and codecs only); per-machine recording switches; per-visit
  event codes in the session journal.
- Keeps separate: roadmap step 9 — the atomic state write and the session lock — stays its own
  `fix/` concern of the same file layer. This decision makes it cheaper, not different: the state
  file stops growing with the run, and the stream's own consistency is a line appended or not.
- Leaves open: the `llm` details member (defined by ADR 014 when it lands); retention beyond the
  session (nothing rotates; the ADR 010 cap bounds a session's stream); a schema version marker for
  the record, taken only if a migration ever forces it; a rollback marker in the trail (recovery
  note (d), undecided).

## Related ADRs

- Depends on: ADR 002 (visits, guards, transitions — what a record names), ADR 003 (the
  persistence contract the stream extends), ADR 006 (the engine-owned trail and applied-writes
  semantics), ADR 008 (the session directory and path policy), ADR 011 (artifacts as the payload
  channel), ADR 013 (§9, names not values), ADR 018 (the bounded read discipline).
- Touches: ADR 004 (nothing new is snapshotted into the session record), ADR 010 (the cap bounds
  the stream), ADR 014 (Draft; its §4 audit lands in this channel as the `llm` details when that
  ADR is edited on its own branch), ADR 017 (the ordinals a record carries).

## Implementation notes

- The stream file name and the record's serialized field set are the implementation's choice; the
  walkthrough documents both when the class 4 evidence is run.
- The freeze-gate run: `folder-inventory-to-csv` over a prepared tree, the walk read back with
  `show-records` whole, per node and tailed, added to the walkthrough.
- Entering Implementing creates `feature/adr_021-node-record-channel`.

## Change log

- 2026-08-24: opened as Draft in session `2026-08-24-architecture-3`, executing decisions 2–4 of
  investigation `2026-08-24-investigation-1`: the record scope is fixed as every visit,
  engine-written, names not values (the opt-in, switched, and logging-framework framings are
  rejected as alternatives D–F); the destination is decided against the four investigated
  alternatives — an append-only stream outside the state, with artifacts kept as the payload
  channel; the consumer is the after-the-fact reader with class 4 evidence on
  `folder-inventory-to-csv`, so the freeze does not wait on the ADR 014 gate variants; roadmap
  step 9 is kept a separate concern of the same file layer.
