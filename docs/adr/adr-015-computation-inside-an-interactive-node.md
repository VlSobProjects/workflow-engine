# ADR 015: Computation inside an interactive node

## Status
Draft

## Active branch
—

## Context

ADR 013 delivered one interactive action, `ask`, and it is purely declarative: it renders a
presentation from configuration and turns a validated answer into the node's output. On the automatic
side the core has three shapes that carry a registered function — `function`, `functions`, and `stop`,
which runs one if it is configured. The interactive side has none.

Within a week of shipping it, two workarounds appeared in this repository, both symptoms of the same
absence:

- **`echo_value` in front of a guard.** A value guard compares `output.output_text`; a decision that
  arrives as a declared answer value is data, not a route, so surfacing it costs a node whose only job
  is to put a parameter into an output text (recorded in the ADR-0083 coverage note).
- **`CHECK` and `COLLECT` around a question.** A loop that keeps every answer needs a node to append
  it and a node to decide whether there is enough, because the `ask` node can do neither (session
  `2026-08-19-implementation-15`).

Both are legible and both work. What they show is that the interactive node is the only node in the
engine that cannot compute anything, and that the gap is paid for in graph size every time.

Talking to an AI sharpens it. An answer from a model arrives as text that is nearly, but not exactly,
what the flow needs: a synonym instead of a declared option, a JSON block wrapped in prose, a path
that needs normalizing, a report that should become an artifact. Today every such adjustment is either
an instruction in the prompt ("answer exactly `approved`") or a following node.

ADR 013 reserved this space rather than missing it: alternative C rejected an answer typed by the
action class "as the primary mechanism, possible later as a specialization". This ADR is that
specialization, and it is additive — ADR 013 is Accepted and stays as it is.

Constraints:
- ADR 002: a node is one action and an ordered list of guarded transitions. The graph is the audit
  surface, and work done inside a node is work the journal cannot explain.
- ADR 013 §5 and §6 are frozen: the refusal rules and the meaning of re-presenting a question.
- ADR 006: the engine owns the bus, and a node's writes are applied when the step is taken — so at the
  moment an answer is processed, its values are **not** on the bus yet.
- Phase 2 is additive; a registered component is the sanctioned extension mechanism (ADR 005).

## Decision

Draft. The direction below is proposed; the open points are listed at the end of this section.

### 1. Post-processing of an answer is in scope, pre-processing is not — yet

An interactive node may run a registered function **after** an answer has been accepted, before the
answer becomes the output the node's guards see. That is the half with the evidence behind it: both
workarounds above are post-processing, and normalizing what a model said is post-processing.

Preparing the *question* by running a function first is deliberately left out of this ADR, for two
reasons. It competes with prompt templating for the same job — most of its uses are "assemble the
question text from state", which is what interpolation would solve properly (ADR 012 deferred §1,
ADR 014 open point 1) — and it collides with ADR 013 §6: a question is re-presented on a plain
`resume`, consuming neither an attempt nor a visit, and a pre-function would make re-presenting
execute code. Either the function must be required to be idempotent, which the engine cannot check,
or §6 changes. Neither is worth deciding before the templating question is answered.

### 2. The boundary: data of the exchange, not steps of the process

Computation inside an interactive node transforms the question and the answer. Anything that deserves
its own line in the journal — a step that can fail on its own terms, that a transition should be able
to route around, that an operator should see as a visited node — stays a node.

This is the point of the whole ADR and the thing to hold: the two workarounds are verbose, but
`guard_results["CHECK"]` answers "why did the loop exit" and a `COLLECT` failure is a node failure
with its own error code. A function hidden inside `ask` has no guard record, no counters and no route
around it. Trading that away for brevity is only worth it where the work is genuinely a data
adjustment.

### 3. The function receives the answer, because the answer is not on the bus yet

The engine applies a node's `param_writes` when the step is taken, which is after the transition is
selected. At post-processing time the answered values exist only inside the pending output, so a
`param.<name>` reference in the function's configuration would resolve to the previous value or fail.

The bound answer is therefore **injected**, the way `state`, `output` and `action_output` already are
for registered functions: a post function declares a parameter for the answer and receives its values,
its text, its status and its error code. Its configured `function_parameters` keep resolving against
the state as everywhere else, so it can combine the answer with what the run already knows.

### 4. The function's result is the node's output

The post function returns an `ActionNodeOutput`, and that output is what the node's transitions see
and what the engine applies: its `output_text` is what value guards compare, its `param_writes` are
what lands on the bus, its `error_code` routes like any other node error, and its artifacts register
normally.

That is what removes both workarounds at once: putting the decision into `output_text` makes it
routable, and returning an `APPEND` write makes the node accumulate.

### 5. A failing post function is a node failure

A post function reports an error the way every registered function does: an error code in its result,
or an exception the engine turns into a node error. The node then routes on that code like any other
failure, and its `max_attempts` allowance applies.

### 6. Refusal comes first, and is untouched

The ADR 013 §5 preconditions and validation run before any of this: an answer that is refused never
reaches user code, applies nothing and journals nothing. Post-processing operates only on an answer
that the engine has already accepted and bound.

### 7. The journal keeps recording the answer as supplied

`interactive_answered` continues to record what arrived — the actor, the answered names and their
codecs. What the post function made of it is the node's output, journaled the way every node's output
is. The audit distinction between "what was supplied from outside" and "what the engine computed"
(ADR 006) is what makes this the right split.

### Open points to settle before leaving Draft

1. **Shape.** A separate action (`ask_function`, mirroring how the automatic side separates
   `ActionWithFunction` from the rest), or optional configuration keys on `ask` (mirroring `stop`,
   which runs a function only when one is configured). Both have a precedent in this core. A separate
   action keeps `ask` and its help card simple; optional keys avoid a second interactive action an
   author has to choose between.
2. **May a post function change the answered values, or only add to them?** Returning `param_writes`
   freely means the value written for a declared name can differ from the value the caller sent, while
   the journal records the name as answered. That may be exactly the point (normalization) or a hole
   in the audit story, and the answer decides whether the declaration is a contract about what was
   *supplied* or about what was *stored*.
3. **Write modes.** ADR 013 alternative H rejected letting an answer choose its write mode. A post
   function returning `APPEND` reintroduces that by the back door — deliberately, since accumulation
   is one of the two motivating cases — so the ADR has to say plainly that the restriction is on the
   *answer document*, not on the node.
4. **Is the answer consumed when the post function fails?** The answer was accepted and journaled, and
   then the node failed. On a retry the same question is asked again, which is right; but the journal
   then holds an `interactive_answered` for an answer whose values never reached the bus.
5. **One function or several.** The automatic side needed `functions` as well as `function`. Whether
   the interactive side needs the same is unknown; the default should be one until it is not.
6. **When pre-processing is reconsidered**, and against which decision — the templating question, or
   evidence from the first flows that a question genuinely has to be computed rather than composed.

## Alternatives considered

### A. Keep the graph as the only place to compute
Do nothing in the core: an author writes the extra nodes, exactly as the two workarounds do. Free, and
it keeps every step visible in the journal with its own guard results and counters. Rejected as the
only answer because the price is paid on every interactive flow and it is paid twice for an AI far
end, where adjusting an answer is the normal case rather than the exception. Kept as the rule for
anything above the boundary of §2.

### B. Declarative micro-transforms in the answer declaration
Let a declared answer entry carry small transformations — `trim`, `lower`, `one_of` with a synonym
map — so normalization needs no function at all. Cheap for the common cases, keeps the node
declarative, and stays inside the ADR 012 declaration shape. Rejected as the primary mechanism: the
set of transforms is never finished, each addition is a core change, and the moment a flow needs one
that is not in the list it is back to a node. Worth revisiting as sugar over the function form.

### C. An external interactive action
A team registers its own `BaseInteractiveAction` subclass through `external_modules`; the extension
point exists today and needs no ADR. Rejected as the answer for the core: normalizing an answer from a
model is not team-specific, and leaving it outside means every workplace invents its own and none of
them appear in the help contract.

### D. A node-level pre/post concept for every action
Generalize: any node may declare functions that run before and after its action. Uniform and powerful.
Rejected: it dissolves ADR 002 — a node stops being one action and becomes a small program, the guard
results stop explaining the node, and the same work becomes expressible in two places with no rule for
choosing. The interactive node is asking for this because it is the only one that cannot already run a
function; the automatic ones can.

### E. Fold it into ADR 014
Let the LLM node own answer parsing, and leave `ask` declarative. Tempting because the motivating case
is a model reply. Rejected: ADR 014 is about the engine calling a model itself, while this is about an
answer arriving from outside — an operator's answer needs normalizing too, and the ADR-0083 `FQ` loop
has no model in it at all.

## Consequences

- Enables: routing on an answered value without a surfacing node; accumulating an answer in the node
  that asked; normalizing a model's reply before it decides anything; turning an answer into an
  artifact in one node.
- Costs: a second way to do things that the graph can already do, which needs the boundary of §2 to be
  stated and held in review; a new injected parameter for registered functions; operator metadata and
  help for whichever shape §1 of the open points chooses.
- Closes off: nothing in ADR 013. The answer contract, the refusal rules and the journal are unchanged;
  this adds a stage after them.
- Leaves open: pre-processing, and with it the question of whether re-presenting a question may run
  code.

## Related ADRs

- Depends on: ADR 013 (the answer contract this computes on), ADR 002 (node composition and guards),
  ADR 005 (registered components), ADR 009 (operator help for the new shape).
- Touches: ADR 006 (what reaches the bus and what the journal records), ADR 012 (the declaration shape
  the answer reuses), ADR 014 (which may consume the same post-processing for a model reply).
- Supersedes: nothing.

## Implementation notes

No POC is proposed. The open points are contract questions rather than feasibility questions: the
engine already runs registered functions with injected parameters, and the interactive path already
produces an `ActionNodeOutput` that the post function would replace.

The evidence that should settle open point 6, and probably 1, comes from the first goal of phase 2 —
building the ADR-0083 scenario as a real flow
(`docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`). This ADR should not leave Draft
before that flow exists, so that the shape is chosen against a written flow rather than against an
imagined one.

## Change log

- 2026-08-20: opened as Draft in session `2026-08-20-architecture-1`, from two workarounds that
  appeared within a week of ADR 013 shipping and from the needs of an AI far end. ADR 013 alternative C
  had reserved the space.
