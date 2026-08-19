# ADR 013: Interactive exchange and typed answer contract

## Status
Draft

## Active branch
—

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

Draft. The direction below is proposed; the open points are listed at the end of this section.

### 1. One contract, whoever answers

The engine does not model "agent" and "operator" as different nodes. There is one interactive
action and one answer contract. Who answered is data about the answer, recorded in the journal, not
a property of the node.

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

The declaration is part of the presentation the engine returns, so a caller — agent or human
tooling — knows the schema of the answer without reading the workflow file.

### 3. Pausing

When the run reaches an `ask` node, the engine returns the presentation, journals an engine event
(`workflow_paused_interactive`, carrying the node id and the declared answer names), saves state and
stops. The CLI reports it as a paused workflow (exit code `2`), `data` carrying the presentation and
the answer declaration.

### 4. Answering

`resume` gains an additive option to submit the answer for the paused node (proposed
`--answer <json>` and `--answer-file <path>`, mutually exclusive). The answer is a JSON object with:

- `status`: `success` | `failure` | `escalate`;
- `values`: a mapping of declared answer names to values, decoded through the declared codec by
  the same rule `--input` uses (JSON-parsed with raw-string fallback; an untyped value stays a
  string); unknown names and missing `required` names are rejected before anything is applied;
- `error_code` and `message` when `status` is `failure`; the code must come from the node's
  declared error catalogue or be the generic `answer_failed`;
- `actor`: free label of who answered (e.g. `operator`, `agent:<name>`); optional, defaults to
  `unspecified`.

A `success` answer becomes an `ActionNodeOutput` with `SET` `param_writes` for the values and runs
through `_proceed_with_output`: the node's guards and transitions decide where the run goes, exactly
as for a computed output. A `failure` answer becomes an output with the error code, and the normal
retry machinery applies (a self-loop or an `attempts` transition, bounded by `max_attempts`). The
engine never writes the answer to the bus directly.

The answer is journaled as an operator-side event (`interactive_answered`) carrying the node id,
status, actor, and the answered names and codecs — never the values, mirroring `inputs_set`.

### 5. Escalation

`status: escalate` means the far end could not answer and hands the question to someone else
(typically agent → operator). The node stays paused, no attempt is consumed, the escalation is
journaled (`interactive_escalated`, with actor and message), and the next `resume` re-presents the
same node. A node may declare an `audience` hint (`agent` | `operator` | `any`) that the
presentation carries; the engine does not enforce it — it has no way to know who is reading.

### 6. Pause is not failure

This ADR covers continuing a paused node. Reopening a session in terminal `FAILED` state to finish
it by hand is a separate capability and is explicitly out of scope; it stays in the recovery note.

### Open points to settle before leaving Draft

1. Transport form: a JSON object on `resume` (above) versus repeated typed flags
   (`--answer NAME[:TYPE]=VALUE`, the `--input` grammar) plus `--answer-status`. The flag form is
   shell-friendly for humans; the JSON form is the natural one for an agent and carries the status
   and message without inventing more flags. One of them, not both, in phase 2.
2. Whether `escalate` is an answer status (above) or a third terminal of the presentation the agent
   simply does not answer; and whether `audience` deserves to exist at all in the first version.
3. Whether the presentation returned by the CLI is the `PresentResponse` as is, or a reduced
   stable contract, given that `PresentResponse` is also the engine's vehicle for limit and failure
   reports.
4. Whether a paused `ask` node counts in `nodes_visited` once or once per answer attempt.
5. Which of the existing `PresentResponse` defaults (`default_hints`, `default_submit`) survive
   once the answer is declared.

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

## Consequences

- Enables: mid-run input from an agent or an operator with schema, validation, audit and routing
  through guards; manual takeover of a step an automated node cannot complete (recovery note (a));
  the answer declaration that ADR 014 reuses for LLM outputs.
- Costs: a new core action, a `resume` option and result-data extension, three session event codes,
  and a state marker for "paused at interactive node awaiting answer" if the current node id is not
  enough to derive it.
- Closes off: answering a node by writing the bus from outside; per-audience action types.
- Leaves open: reopening failed sessions; workflow-definition introspection without running
  (ADR 012 deferred §3), which an agent driver will want next.

## Related ADRs

- Depends on: ADR 006 (bus and journal), ADR 007 (command contract and exit codes), ADR 012
  (codec-typed binding rule, `inputs` declaration shape).
- Touches: ADR 002 (the answer runs through guards and transitions), ADR 009 (the action and its
  answer declaration in the help contract), ADR 011 (artifact references in presentation text).
- Consumed by: ADR 014 (answer declaration and binding).

## Implementation notes

Candidate POC question, if the decision cannot be settled on paper: can an external agent (a script
acting as one) drive the two shipped example workflows extended with one `ask` node through the CLI
alone — pause, read the schema, answer, escalate, resume — with the journal showing the actor on
every answer? Existing pieces to reuse: `BaseInteractiveAction`, `PresentResponse`,
`ActionNodeOutput.from_args`, `_proceed_with_output`, the ADR 012 input decoding.

## Change log

- 2026-08-19: opened as Draft in session `2026-08-19-architecture-1`, from ADR 007 §4 and the
  recovery roadmap note (a).
