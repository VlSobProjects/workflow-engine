# ADR 013: Interactive exchange and typed answer contract

## Status
Implementing

## Active branch
`feature/adr_013-interactive-exchange`

## Context

Phase 2 puts something other than a deterministic function at the far end of a node: an AI agent,
an operator, or an agent that escalates to an operator. The engine already has half of the
mechanism and none of the contract:

- `BaseInteractiveAction.present` returns a `PresentResponse`, the engine returns it to its caller
  and stops; on the next call `ActionNodeOutput.from_args` decodes an output for the paused node and
  `_proceed_with_output` runs it through the node's guards and transitions. This is exercised by
  engine tests only.
- No core action subclasses `BaseInteractiveAction`. The only operator path that fabricated a paused
  node's output — the `resume` parameter flags — was broken, uncontracted, and removed by ADR 012.
  ADR 007 §4 defers interactive input to phase 2 explicitly.
- `PresentResponse` describes the question richly (instruction, options, constraints, examples,
  errors) but says nothing machine-readable about the *answer*: `expected_input` is free text.
  `SubmitResult`/`SubmitStatus` exist and are unused.
- Nothing of the presentation reaches the caller. `run` and `resume` copy its description into the
  result message and merge its errors; no other field leaves the process.
- Nothing records who answered. The session journal distinguishes engine events from operator
  commands (ADR 006), but an answer to a paused node has no actor.

The recovery roadmap note (2026-08-18) fixes three design points for this mechanism: the answer
routes through the node's guards and transitions, not around them; the journal separates
"engine computed" from "supplied from outside"; and continuing a paused node is distinct from
reopening a failed session.

Constraints:
- ADR 006: every bus write is a node output applied and journaled by the engine; resume is
  deterministic from persisted state.
- ADR 007: the command contract is extended additively; exit code `2` already covers "awaiting
  operator action (interactive stop)".
- ADR 012 closed mid-run external writes to a started run on purpose; the answer surface is
  introduced deliberately here, not by widening `set-input`.
- Phase 2 is additive (session `2026-08-19-architecture-1`): existing nodes, guards and transitions
  keep their semantics.

## Decision

### 1. One contract, whoever answers

The engine does not model "agent" and "operator" as different kinds of node. There is one
interactive action and one answer contract. Who answered is data about the answer, recorded in the
journal, not a property of the node.

A node that asks the operator a prepared question, a node that asks an agent to choose a branch, and
a node that asks an agent to go away, act, and report back differ only in the text of the
presentation and in who reads it. The engine treats all three identically, so it needs no taxonomy
of interactive node types.

### 2. A core interactive action with a declared answer

A core action (working name `ask`, subclass of `BaseInteractiveAction`) whose node configuration
carries:

- the presentation: the `PresentResponse` fields an author wants to set (title, instruction, goal,
  options, constraints, examples, error catalogue), with `param.`/`output.`/`artifact.` references
  resolved by the engine as for any node;
- an `answer` declaration: an ordered list of entries in the shape of the ADR 012 `inputs` block —
  `name`, optional codec `type`, `required` (default true), optional description. It states which
  parameters a valid answer must carry and how they are typed. It is the machine-readable
  replacement of `expected_input`.

The `answer` declaration and the workflow `inputs` block are one shape with one validator, not two
that happen to look alike.

The declaration is part of the presentation the engine returns, so a caller — agent or human
tooling — knows the schema of the answer without reading the workflow file. A command that describes
a workflow definition without running it is therefore not a prerequisite for this decision.

### 3. Pausing

When the run reaches an `ask` node, the engine returns the presentation, journals an engine event
(`workflow_paused_interactive`, carrying the node id and the declared answer names), saves state and
stops.

The paused position needs no new state field: `state.current_node_id` names the node, and whether
its action is interactive is read from the built node.

The CLI reports a paused workflow (exit code `2`) and carries a `question` block in `data`: the node
id, the presentation, the answer declaration and the error catalogue. That block, and not
`PresentResponse` itself, is the caller-facing contract. `PresentResponse` is also the engine's
vehicle for setup errors, budget stops, node failures and completion; publishing it would tie four
unrelated reports to one frozen shape.

### 4. Answering

`resume` gains two mutually exclusive options: `--answer <json>` and `--answer-file <path>`. The
answer is a JSON object with:

- `status`: `success` | `failure`;
- `values`: a mapping of declared answer names to values. Each value is decoded by the codec
  declared for its name; a name declared without a type is bound as given. The JSON-parse-with-raw-
  string-fallback rule of `--input` belongs to the string transport of a command-line flag and does
  not apply here: a JSON answer already carries typed values;
- `text`, optional: the `output_text` of the node, and therefore `state.outputs[<node id>]` and what
  a `save_as` on that node stores. It defaults to the empty string. Value guards (`equals`,
  `contains`, `starts_with`, `ends_with`) read it, so a free-form answer can be routed on without
  declaring a parameter for it;
- `error_code` and `message` when `status` is `failure`; the code must come from the node's declared
  error catalogue or be the generic `answer_failed`;
- `actor`: free label of who answered (e.g. `operator`, `agent:<name>`); optional, defaults to
  `unspecified`.

A `success` answer becomes an `ActionNodeOutput` with `SET` `param_writes` for the values and runs
through `_proceed_with_output`: the node's guards and transitions decide where the run goes, exactly
as for a computed output. `SET` is the only write mode available to an answer: an answer is a value,
not an operation on the bus. Accumulating answers across a loop is the work of a following node.

A `failure` answer becomes an output with the error code, and the normal retry machinery applies (a
self-loop or an `attempts` transition, bounded by `max_attempts`). The engine never writes the answer
to the bus directly.

### 5. When an answer is refused

An answer is accepted only when the action of the current node is interactive and the last session
event is `workflow_paused_interactive`. A run paused at a limit, a failed run and an automatic node
are refused: an answer to a node that did not ask is the fabricated node output ADR 012 removed.

Refused as well, before anything is applied: an undeclared name, a missing `required` name, a value
the declared codec cannot decode, and an `error_code` outside the node's catalogue.

Every refusal is a command error (exit code `4`) that applies nothing and records no session event.
The journal holds what happened to the run, and a refused command did not happen to it; this is how
a refused `set-input` already behaves.

### 6. Re-presenting a question

`resume` without an answer, at a paused interactive node, presents the same node again unchanged. No
attempt is consumed and no visit counted.

This is all an escalation needs: a far end that cannot answer simply does not answer, and whoever
calls next — a human, typically — is shown the same question. The engine has no way to know who is
reading, so it declares nothing about the intended audience.

### 7. Pause is not failure

This ADR covers continuing a paused node. Reopening a session in terminal `FAILED` state to finish
it by hand is a separate capability and is explicitly out of scope; it stays in the recovery note.

### 8. Counting

An `ask` node is counted like every other node: a transition that returns to it consumes an attempt
and is bounded by `max_attempts`, and `nodes_visited` grows only when the run leaves it. A
re-presented question consumes neither, so the ADR 010 budget does not bound how long a question may
stay open. That is intended: the budget bounds engine work, and a question waiting for an answer is
not engine work.

### 9. The answer in the journal

The answer is journaled as an operator-side event (`interactive_answered`) carrying the node id, the
status, the answered names with their codecs, and the `actor` label in the event details — never the
values, mirroring `inputs_set`.

The label lives in the details because `SessionEvent.actor` is the engine/operator distinction of
ADR 006 and stays two-valued. Who supplied an answer is a property of the answer, not a third kind
of actor.

## Alternatives considered

### A. Typed answer through free-form parameter flags on `resume`
The phase 1 shape that ADR 012 removed: the caller fabricates `param_writes` by name with no
declaration. Cheap, but the caller must know the workflow file to answer, nothing validates the
answer, and an agent gets no schema. Rejected; it is the situation this ADR replaces.

### B. Separate action types for operator input and agent input
Two actions, two presentations, two submission paths. Lets each be tailored, but duplicates the
contract, forces the author to decide at authoring time who will answer, and makes escalation a
cross-type transition. Rejected in favour of one contract with an actor label.

### C. Answer typed by the action class, not by declaration
A Python interactive action knows its answer schema in code; the JSON node only names the action.
Keeps the node config small, but every new question shape needs a new class, and the schema is
invisible to `help-component` and to the paused-run result unless each class re-exposes it. The
declarative form reuses ADR 012 and ADR 009 surfaces; rejected as the primary mechanism, possible
later as a specialization.

### D. A server or MCP transport first
An always-on process the agent talks to. Removes the resume round-trip but introduces a runtime
the project has deliberately not had, a second public contract, and process-lifetime questions.
Deferred: the CLI/JSON contract here is what such an adapter would wrap later.

### E. Escalation as a third answer status
`status: escalate` leaves the node paused, consumes no attempt and is journaled under its own code,
with an `audience` hint (`agent` | `operator` | `any`) on the node. It reads well beside `success`
and `failure`, and it names the agent-to-operator handover explicitly. Rejected: it does nothing
that `resume` without an answer does not already do, and the `audience` hint it invites is a
declaration the engine can neither check nor enforce. A distinct record for "the far end gave up"
can be added later if a run needs to tell it apart from "nobody has answered yet".

### F. Typed flags instead of a JSON answer
`--answer NAME[:TYPE]=VALUE` repeated, in the `--input` grammar, plus `--answer-status`,
`--answer-error` and `--actor`. Shell-friendly and consistent with `set-input`. Rejected as the
first form: an answer carries a status, a message and an actor beside its values, so the flag form
needs five flags and rules about which combine with which; a collection value has to be JSON-parsed
inside the flag string anyway, reintroducing the second decoding rule §4 removes; and the primary
caller is a program, not a hand. The flag form stays available later as an additive second transport
if answering by hand proves painful.

### G. Returning `PresentResponse` as the caller-facing document
Serialize the dataclass into `data` and be done. The cheapest option today, and it exposes every
field an author can set. Rejected: the same class carries setup errors, budget stops, node failures
and completion, so publishing it makes any future change to any of those a breaking change of the
command contract. §3 exposes a reduced block instead.

### H. A write mode in the answer declaration
Let a declared name carry `APPEND` or `REPLACE` beside `SET`, so that a loop of questions
accumulates into one list parameter inside a single node. Saves two nodes in an adaptive-questioning
flow. Rejected: it makes the answer declaration diverge from the ADR 012 `inputs` shape it is meant
to be, and it hands bus semantics to whoever answers. The same result is one following node using
the existing collection-writing functions.

## Consequences

- Enables: mid-run input from an agent or an operator with schema, validation, audit and routing
  through guards; manual takeover of a step an automated node cannot complete (recovery note (a));
  the answer declaration that ADR 014 reuses for LLM outputs.
- Costs: a new core action with its ADR 009 operator metadata, two `resume` options and a `question`
  block in the command result, two session event codes, the extraction of the input declaration and
  of the codec decoding into forms that both `inputs` and `answer` use, and the removal of the two
  `PresentResponse` defaults (`default_submit`, `default_hints`) that describe the unstructured
  protocol the declared answer replaces.
- Costs nothing in the state model: the paused position is `state.current_node_id`, and the actor
  label rides in the details of an event.
- Closes off: answering a node by writing the bus from outside; per-audience action types; an answer
  that chooses its own write mode.
- Leaves open: reopening failed sessions; workflow-definition introspection without running
  (ADR 012 deferred §3), which this decision does not require; a budget checkpoint routed to a node
  inside the graph instead of the out-of-graph pause of ADR 010.
- Leaves open, found by the review of the delivered implementation and recorded in
  `docs/architecture/notes/2026-08-19-interactive-exchange-publishing-boundary.md`: that the
  internal/published boundary is held by one function rather than by the shapes (`PresentResponse`
  keeps the fields the declared answer replaced), that `actor` is an audit label with no identity
  contract behind it, and that the published `question` block carries no version of its own.

## Related ADRs

- Depends on: ADR 006 (bus and journal), ADR 007 (command contract and exit codes), ADR 012
  (codec-typed binding rule, `inputs` declaration shape).
- Touches: ADR 002 (the answer runs through guards and transitions), ADR 009 (the action and its
  answer declaration in the help contract), ADR 010 (a re-presented question consumes no budget),
  ADR 011 (artifact references in presentation text).
- Consumed by: ADR 014 (answer declaration and binding).

## Implementation notes

No POC: the pause mechanism already exists and is covered by engine tests, and no open question
remains that only code could answer.

Reuse rather than rebuild:
- `BaseInteractiveAction` and the interactive branch of `_start_engine` — the pause already works;
- `_proceed_with_output` — the answer path needs no change to guard or transition handling;
- `ActionNodeOutput.from_args` — the existing decoding of an externally supplied output (dropped
  during implementation: see the change log);
- `WorkflowModel._validate_inputs` — extract it so `inputs` and `answer` share one validator;
- `decode_input_value` — split it so that decoding an already-parsed value by its codec is reachable
  without the command-line string rule;
- the collection-writing functions, for accumulating answers across a loop of questions;
- `_require_bound_inputs` — the shape of a setup-time precondition that refuses a command.

Touched, as delivered: `models/workflow.py` (the extracted declaration validator), `inputs.py` (the
extracted codec decoding), `exceptions.py` (`WorkflowAnswerError`), `actions/action_present.py`
(`AnswerContract`, the two removed defaults), `actions/base_actions.py` (`answer_contract`), the new
`actions/action_ask.py`, the new `answers.py`, `bootstrap/plugin_manifest.py`, `output.py` (the
removed `from_args`), `engine.py`, `models/state.py` (event codes, status derivation, actor code
lists), `cli/main.py`, `cli/use_cases.py`, `README.md`, `docs/architecture/overview.md`,
`examples/approve-and-copy.json`, and three test modules. `cli/contract.py` needed no change: the
question rides in `data`, which the command result already carries.

## Change log

- 2026-08-19: opened as Draft in session `2026-08-19-architecture-1`, from ADR 007 §4 and the
  recovery roadmap note (a).
- 2026-08-19: all five open points settled and the ADR moved to Implementing (session
  `2026-08-19-architecture-2`). The transport is a JSON answer on `resume`, with the flag form kept
  as alternative F. `escalate` and `audience` are dropped in favour of re-presenting on a plain
  `resume` (alternative E). The caller-facing presentation is a reduced `question` block rather than
  `PresentResponse` (alternative G). The counting question was answered by the rule the engine
  already applies instead of a new one. `default_submit` and `default_hints` are removed. Three gaps
  the draft had not named were closed in the same pass: what the `output_text` of an answered node
  is (the new `text` field), when an answer is refused (§5), and that `values` are written with
  `SET` only (alternative H).
- 2026-08-19: implemented on `feature/adr_013-interactive-exchange` (session
  `2026-08-19-implementation-11`). Six points the text left to the implementation, recorded here
  because they are contract, not mechanics:
  1. The declaration and the error catalogue travel as one `AnswerContract` on the presentation, and
     the catalogue is **not** `PresentResponse.errors`: that field says what actually failed, and
     filling it with a catalogue is the defect the `fix/successful-run-reports-errors` session
     removed. `BaseInteractiveAction.answer_contract()` is what the engine reads, so it validates an
     answer without knowing which interactive action asked.
  2. `ActionNodeOutput.from_args` and the `output` parameter of `start_workflow` are removed instead
     of reused. Nothing called them, and `from_args` read `args.input`, which ADR 012 gave a
     different meaning. `start_workflow` now takes the `answer` in their place.
  3. A `failure` answer carries no `values`: it answered nothing, so a half-answer is refused rather
     than silently dropped. Unknown top-level fields are refused for the same reason.
  4. The `SET` writes of an answer allow overwriting, because a question asked again in a loop
     answers the same names.
  5. The `answer` declaration is a required key of an `ask` node; a question that binds no parameter
     declares `[]` explicitly and is routed by its answer text.
  6. The published block names the generic failure code as `generic_error_code`, so a caller learns
     `answer_failed` from the question instead of from this document.
