# ADR 002: Node composition — one action and guarded transitions

## Status
Implementing

## Active branch
`feature/adr_002-node-composition`

## Context

The engine executes a graph of nodes defined in JSON. This decision answers what a node is made of
and what contract holds between its parts.

The origin contract, ADR-0083 in the `java-claude-ai` project, modelled a node as a closed enum of
node types, each carrying its own behaviour, validation and branching. This engine has a different
purpose: behaviour is composed from configuration, so a new capability is a new registered component
rather than a new node type. Interaction with an AI agent is a stream of instructions with
deterministic steps around them, and the deterministic part must be describable in configuration.

The implementation currently has three parts per node: an action, a list of validators, and a list of
transitions. Reading the code and the example configurations shows that the middle part does not earn
its own layer.

- A validator and a transition guard are the same thing: a predicate over the result and the state.
  `ValidatorBasedTransition` already reuses a validator as its guard.
- What differs is the default. A validator denies by default: if it does not hold, the node failed. A
  transition passes through by default: if its guard does not hold, the next rule is tried.
- In the four example configurations every use of `validators` is a post-condition assertion, mostly
  `is_output_exist_file`, and none of them feed a branch. Two nodes in `simple_workflow.json` carry a
  validator and no transitions at all.
- The validator sees only `output_text`. It cannot see the error code, so a failed action and a
  successful one are indistinguishable to it.
- A failing validator produces the literal code `validation_failed` in the engine, while
  `errors_registry` declares `validation_output_error`. Neither identifies the rule that failed, so a
  transition cannot branch on which check broke, and an operator cannot reconstruct why the workflow
  took a given edge.
- Combination is expressible in two places: the engine conjoins node level validators with `all`,
  while `CombinedOutputValidator` offers its own conjunction and disjunction. The latter reads an
  `operator` key from each child and folds left without precedence, so `[a, b(or), c(and)]` means
  `(a or b) and c`, which the author of a configuration cannot see.

## Decision

A node is **one action and an ordered list of guarded transitions**. There is no validation layer at
runtime.

### Runtime model

1. **Action** — exactly one per node. It performs the work and produces one result. An error is a
   value in that result, not an exception.
   The reason for exactly one is the interactive case: one node is one exchange with the agent or the
   user, so that what was produced can be checked before the workflow continues. For automatic work
   the same boundary is what makes a step observable. An action type may internally run a configured
   sequence of registered functions; that is a property of that action type, not a second action in
   the node.
2. **Guarded transition** — zero or more, ordered. Each has a guard and a target. Guards are
   evaluated in order and the first one that holds selects the target.

A **target** is either the identifier of a node declared in the workflow, or a terminal outcome:
failure of the node with a code, or the end of the workflow. Targets are static, so the whole graph
is checkable before execution. A transition never mutates the state and never constructs a node.

A transition whose target is a node is a **routing** transition. One whose target is terminal is not.
The distinction matters only for the rule below on unmatched transitions.

A guard may be negated, which is how a post-condition is expressed: the target is taken when the
check does **not** hold.

Retry is expressed as a transition whose target is the node itself, or by the `attempts` flag on a
transition, which retries the node before taking the declared target. Both are bounded by the same
allowance, and a node that exhausts it fails. The `attempts` flag needs a target that is a node,
because there is nothing to retry before ending or failing. The engine does not retry a node that no
transition asked to retry. How large the allowance is, and how it interacts with a budget for the
whole run, is the subject of the error and retry decision, not of this one.

Guards are the only predicate concept in the engine and come from one registry.

### Guard contract

A guard receives the whole action result and the state, and returns a boolean. In addition it exposes
a **name** that identifies the rule.

The guard does not write anything. The caller passes a list of records to the guard and the guard
appends its own answer to it; the caller then stores that list in the state, under the node being
executed. A guard therefore stays pure and can be evaluated in isolation.

The recorded results are what makes an execution explainable: after the fact, the state says which
rules were evaluated in a node and how each of them answered. A group of guards records every child
it evaluated, so a combination is as readable as a single check.

Because the name identifies the rule, it is also the error code of a node that failed a guard. No
separate code has to be declared in the configuration. A node that fails keeps the message its action
wrote whenever that message still explains the code, so a failure never degrades into a tautology.

Rules for recording:

- The results of one node are an ordered list, not a map keyed by name, because the same guard may
  appear twice in one node.
- Only the results of the latest attempt of a node are kept. The state is written to disk on every
  turn, and the history of attempts is already carried by the attempt counters.
- Short circuiting means a group records only the children it actually evaluated. That is the
  intended behaviour: the record states what was checked, not what was declared.

Guards are pure in a second sense: they have no notion of severity. The same guard is a fatal check
in one node and a branch in another. Whether a matched guard retries the node, routes to another node
or stops the workflow is a property of the transition in the configuration, not of the guard.

A registered guard function keeps returning a boolean and does not change.

### Combination

Guards compose through explicit groups, `all_of` and `any_of`, which nest. The per-child `operator`
key and its implicit left fold are removed. A group has a name of its own, and records the result of
every child it evaluated.

### Configuration surface

The node level `validators` key is kept and stays optional. It is a configuration convenience for the
common case of a post-condition. When the node is built, each entry is expanded into a guarded
transition placed before the declared ones: the guard is the negated check, and the target is failure
of the node with the name of the guard as its code. Nothing of it survives into the runtime node.

An expanded post-condition applies only when the action produced no error code. Without that
restriction a post-condition would also hold against an action that had already failed, and would
replace the real cause with its own name: a failed file copy would be reported as a missing file
rather than as a failed copy. Guards written directly in a transition are not restricted this way,
because branching on how an action failed is exactly what they are for.

If a node declares no routing transition, the workflow ends after that node. If a node declares at
least one routing transition and none of its guards hold, that is a failure of the node, not a silent
stop. A post-condition is not a routing transition, so a node that only asserts something and passes
ends the workflow instead of failing.

## Alternatives considered

### A. Typed node catalogue
One class per node type carrying its own behaviour, validation and branching, as in ADR-0083.
Simplest engine and clearest configuration for a fixed domain. Rejected because every new combination
of behaviour becomes a new type, which the framework author has to add, contradicting the purpose of
this project.

### B. Keep three layers and only repair them
Give each validator a code, let it see the whole result, and leave the layer in place.
Smallest change and no configuration churn. Rejected because it keeps two names, two registries and
two combination mechanisms for one concept, and the duplicated combination logic is already a source
of surprising behaviour.

### C. Collapse fully, remove `validators` from the configuration too
Every assertion is written as a guarded transition to a terminal node.
Conceptually the cleanest: one surface, no expansion step. Rejected because the dominant real usage
is a one line post-condition, which would become four or five lines with a target that has to be
invented, and because the deny by default behaviour would have to be re-established by a rule that
says an unmatched node is an error anyway.

### D. Collapse at runtime, keep `validators` as an optional configuration surface
Chosen. The runtime gains the single concept and the simpler node object of option C, while the
configuration keeps the short form for the case that dominates in practice. The cost is an expansion
step in the node factory and a documented second surface.

### Guard result: outcome object versus name and boolean
An alternative is for a guard to return an outcome object carrying whether it matched, a code
declared in the configuration and a message. Rejected because it requires rewriting every guard class
and its tests to build and combine outcome objects, while producing no information that the recorded
name and boolean do not already carry. The declared code is redundant once the name of the rule is
the code.

### Guard result: exception
A failing guard raises a validation exception carrying the code. Rejected because disjunction then
has to be implemented by catching exceptions, which turns a control flow decision into exception
handling. It also conflicts with ADR 001, where exceptions are reserved for failures that are not
values.

### Recording: the guard writes its own result
The guard writes its name and result into the state itself, so no caller has to. Rejected because the
guard then depends on the state to be callable at all, cannot be evaluated twice, and cannot be
tested in isolation. The caller already holds both the state and the node identity, so it is the
cheaper place to record.

### Target: computed rather than static
A registered function receives the result and the state and returns the identifier of the next node,
which is what `TRANSACTION_REGISTRY` and `FunctionTransition` were built for.
Rejected for now. It is a second concept beside the guard, it makes the graph uncheckable before
execution because the set of reachable nodes is not known, and it moves routing out of the
configuration into code, which is the opposite of the purpose of the engine. No such function has
ever been registered, so nothing is lost by removing it. It can be reintroduced by a later decision
if a case appears that guards cannot express.

## Consequences

- One predicate concept, one registry, one combination mechanism.
- Every target is written in the configuration, so the reachable graph is known before the workflow
  runs and an unknown target is a configuration error rather than a runtime one.
- The runtime node object loses its validator list; the engine loses its separate validation step.
- A guard sees the error code of the action, so recovery paths can branch on how an action failed.
- Every rule that was evaluated is recorded in the state with its answer, which is what makes an
  execution explainable to an operator, and what lets a transition branch on a named check.
- The name of a guard is its error code, so two uses of the same registered function in one node
  cannot be told apart by a transition. If that becomes necessary, a name has to be declarable in the
  configuration.
- The state carries the guard results of every visited node, which is bounded by the size of the
  graph rather than by the length of the run, at the cost of losing the record of an attempt that
  failed and was retried.
- Guards stay reusable because severity lives in the configuration, at the cost of the configuration
  having to state it each time.
- Guard classes and registered guard functions keep their boolean contract, so the change is confined
  to naming, recording and combination.
- The example configurations keep working, because the `validators` key survives. Their meaning
  changes only in that a failure now carries the name of the guard as its code.
- The engine must treat "a routing transition was declared and none matched" as a failure, otherwise
  a typo in a guard becomes a silent stop. Nodes that only assert are unaffected, which is why the
  routing distinction exists.
- Two configuration surfaces express one runtime concept, and the expansion between them has to be
  documented and kept truthful. The restriction that a post-condition does not apply to an already
  failed action is part of that expansion and is invisible in the configuration.
- Routing that cannot be expressed by a guard over a static set of targets is not expressible at all
  until a later decision reintroduces computed targets.

## Related ADRs

- ADR 001, exception architecture. A guard answer is a value; ADR 001 governs the failures that are
  not values.
- The shape of the action result, and whether data passes between nodes through the state or through
  the result, is not decided here and constrains this decision. A guard can only be as expressive as
  the result it receives.
- The registry model, and how components are loaded from outside the project, is not decided here.

## Implementation notes

Delivered in `feature/adr_002-node-composition`.

What the implementation revealed:

- A group guard has to report the answers of its children, but a guard is not allowed to write. The
  caller therefore passes a list to `check`, and each guard appends its own record to it. This keeps
  the guard pure while a group can still record what it evaluated.
- The restriction that a post-condition does not apply to an already failed action needed no special
  case in the engine. The expansion builds `all_of(no_error, not P)`, so it is expressed with the
  same guards as everything else.
- Registered guard functions receive the action result under a new name, `action_output`, beside the
  existing `output`, which stays the output text. Functions that do not declare the parameter are
  unaffected, so none of the eight registered functions changed.
- Implicit retry was removed. The engine used to retry a failed node even when no transition asked
  for it, and then report the run as finished. Retry is now only what a transition declares through
  `attempts`, and an unhandled failure is reported as a failed node.
- `workflow_fields_decoder` in `json_storage` was removed. It was never called and constructed the
  wrong class, and it could not survive the change of shape of a node.
- The rename stopped at the classes that were rewritten anyway. `VALIDATOR_REGISTRY`,
  `register_validator` and the registered functions keep their names, as this ADR states that they
  are unaffected.

Contradictions in the code that this decision resolved:

- `StopOnErrorTransition.transition` returned a constructed node where the contract requires a
  target, so the branch never matched and the node was retried instead of stopping. Replaced by a
  terminal target.
- `FunctionTransition.transition` and `check_error` took a mapping of nodes and returned a node,
  contradicting the base signature. Removed together with the transaction registry.
- `OutputFunctionValidator._validate_output` was declared to return `bool | None`. The guard contract
  is a boolean.
- `StopAction._execute` could return `None` where the contract requires a result. It now returns the
  previous output text.
- Combination through a per child `operator` key folded left without precedence. Replaced by nested
  `all_of` and `any_of`.

Contradictions this decision exposed and deliberately left alone:

- `ForEachOutputParameterNode` and `PopFromQueue` hold iteration state in a field of the action
  instance, but nodes are rebuilt from configuration on every engine turn, so that state is lost.
  Actions must be stateless. Neither is registered, so neither is reachable from a configuration.
- `BaseAction.save_as` is declared with `dataclasses.field` on a class that is not a dataclass, so it
  holds a `Field` object. The engine reads `save_as` from the node configuration, so it is dead.
- `WorkflowNode.set_parameters` and `override_parameters` are read by the engine but never populated
  by the factory, so `set_parameters` in a configuration has no effect.
- Node identity is held in a module level global, which prevents more than one workflow per process.
- Registered functions raise `FunctionArgsError` when an argument fails its check, so a failure that
  this decision treats as a value becomes an exception instead. This is the boundary with ADR 001.
- A configuration error raised while a node is built escapes `sart_engine` instead of becoming a
  response, because nodes are built before the protected section. Two tests record this as the
  current behaviour. ADR 001 owns it.
- A registered function whose parameters are all injected, such as `state` or `output`, cannot be
  constructed: `check_args` binds the signature against the configured parameters only, and reports
  the injected ones as missing. `save_paths_to_deque` and the first node of
  `examples/colect_file_info_workflow.json` are unusable for this reason.
- `state.error_code` and `state.error_msg` are never cleared, so a run that fails a node, recovers
  and finishes still reports the code of the failure it recovered from.
- `state_fields_decoder` is a JSON object hook applied to every nested dictionary, so any node whose
  identifier collides with a state field name, now including `guard_results`, makes a saved state
  impossible to load.

## Change log

- Draft created as a three layer model, describing the implementation as found.
- Revised to two runtime layers after evidence that the validation layer and the transition guard are
  the same predicate with opposite defaults, and that no example configuration uses validation for
  branching. Option D chosen over full collapse to keep the one line post-condition form.
- Guard result changed from a boolean to an outcome carrying a code, which is what makes branching on
  a failed check and explaining a taken edge possible. Exception based signalling rejected because it
  breaks disjunction.
- Outcome object withdrawn in favour of a name on the guard and a record written by the caller. The
  recorded name and answer carry the same information at a fraction of the cost, and the name of the
  rule serves as the error code, so no code has to be declared in the configuration. Recording was
  placed in the caller rather than in the guard to keep guards pure and testable.
- Reviewed against the text as a whole. A transition target was defined explicitly as a node
  identifier or a terminal outcome, and guards were allowed to be negated, because the expansion of
  `validators` did not fit the shape the decision claimed. The expansion was restricted to actions
  that did not already fail, because otherwise a post-condition replaces the real cause of a failure
  with its own name. Routing transitions were separated from terminal ones, because otherwise a node
  that only asserts something would fail on success. The reason for exactly one action per node was
  stated. Computed targets, and with them `TRANSACTION_REGISTRY`, were removed rather than left
  undecided.
- Implemented. The guard contract gained the trace list that the caller passes in, because a group
  has to report its children without writing anything itself. Implicit retry was removed, which the
  decision implied but did not say. Nothing else in the decision changed during implementation.
- Reviewed after implementation. Three defects were found and fixed: a failed node lost the message
  its action had written; the first entry into a node was counted as a retry, so a node reached from
  a predecessor had a larger allowance than the same node at the start; and a transition targeting
  its own node looped forever, because the allowance was applied only to the `attempts` flag. The
  decision text now states that both spellings of retry share one allowance, that `attempts` needs a
  node target, and that a failure keeps the message of its action.
