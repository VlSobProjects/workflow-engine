# Session: ADR 002 implementation

## Type
implementation

## Goal
Implement the node model decided in ADR 002: one action and an ordered list of guarded transitions,
with no validation layer at runtime.

## Completion criteria
- The runtime node holds an action and transitions only.
- Guards are a single concept with a name, negation, nested `all_of` and `any_of`, and their results
  are recorded in the state.
- Transition targets are a node, the end of the workflow, or failure of the node.
- The `validators` key still works from the configuration and is expanded when the node is built.
- Computed transition targets are removed.
- Ruff and pytest pass from the command line.

## Scope boundaries
Only what ADR 002 decides. The defects it merely exposes are left alone: action instances holding
iteration state, the dead `save_as` attribute on `BaseAction`, the module level node registry, and
the unpopulated `set_parameters` on `WorkflowNode`. The error and retry policy belongs to a later
decision.

## Status
completed

## Result

All completion criteria are met.

- `transition/guards.py` holds the single predicate concept: a boolean answer, a name, negation
  through the existing `reversed` key, value guards, a guard over a registered function, a guard over
  the error code, a guard for the absence of an error, and the nested groups `all_of` and `any_of`.
- `transition/base.py` holds `NodeTarget`, `EndTarget` and `FailTarget`, and a transition that is a
  guard, a target and the `attempts` flag.
- `workflow_node_factory` expands each `validators` entry into a leading transition
  `all_of(no_error, not P)` with the target `fail(P)`, so the configuration is unchanged and nothing
  of the validation layer survives into the runtime node.
- The engine makes one ordered pass over the transitions of a node, records the guard answers in the
  state, and ends the run, fails the node, or moves on.
- The transaction registry, `FunctionTransition`, `StopOnErrorTransition` and
  `stop_on_error_node_factory` are removed.

The implementation was then reviewed, and three defects were found and fixed:

- A failed node overwrote the message its action had written with a restatement of the error code,
  so the real diagnostic was lost from the state. The message is now kept whenever it still explains
  the code.
- The first entry into a node was counted as a retry, because the engine updated the state before
  the action of the resumed node had run. A node reached from a predecessor therefore had one more
  attempt than the same node at the start of a workflow.
- A transition targeting its own node looped forever, because the allowance was applied only when
  the `attempts` flag was set. Both spellings of retry now share one allowance, and a node that
  exhausts it fails with `max_attempts_exceeded`.

Verification, run from the command line: `ruff check` reports no findings, `ruff format` reports all
files formatted, and `pytest` reports 48 passed. Twenty five of those tests are new; the engine tests
build their workflow in a temporary directory and do not depend on files outside the repository.

The rename from validator to guard stopped at the classes that were rewritten anyway. The registry
and the registered functions keep their names, as ADR 002 states.

## Decisions

- The trace of guard answers is passed into `check` by the caller and appended to by each guard,
  rather than returned. A group has to report its children, and this keeps the guard from touching
  the state.
- The rule that a post-condition does not apply to a failed action is expressed as a guard,
  `all_of(no_error, not P)`, not as a special case in the engine.
- Registered guard functions receive the action result as a new injected parameter, `action_output`,
  while `output` keeps its meaning as the output text. No registered function had to change.
- Implicit retry was removed. The engine no longer retries a node that no transition asked to retry,
  and an unhandled failure is now reported as a failed node instead of a finished run.
- Guards are not given the state. The capability to write is removed rather than narrowed, because
  without a type checker a narrower annotation enforces nothing. A guard reads the state only
  through the parameter references the engine resolves for it.
- The two registered guard functions that took the state were removed. Neither could ever be built,
  because the argument check binds a signature against the configured parameters only.
- The same check made `action_output` unusable by a registered function. Both injected parameters
  are now declared to it.
- Configuration mistakes are rejected rather than ignored: a non boolean `reversed`, a transition
  declaring both a guard and `errors`, and `attempts` on a target that is not a node.
- A transition remembers where it came from, so a configuration error names the declared transition
  rather than an index shifted by the expanded post-conditions.

## Open questions

- Registered functions raise `FunctionArgsError` when an argument fails its check, so a failure that
  ADR 002 treats as a value becomes an exception. This is the boundary to settle in ADR 001.
- Configuration keys are checked one by one, by hand, in four places. Every key that was not checked
  turned out to accept nonsense silently: `reversed`, `errors`, `all_of` and `stop` were all fixed
  during this session after a question about one of them. A rule that every key has a declared type,
  and that a mismatch names the key, would remove the class rather than the instances. Material for
  ADR 001.
- Material for ADR 001: `registry/errors_registry.py` was removed as dead code. It held an
  unfinished idea, a catalogue mapping every error code to a description, filled by a decorator at
  import time. Nothing ever used it, and the engine produced codes it did not declare. Whether such
  a catalogue is worth having, now that the name of a guard is an error code, is a question for the
  exception architecture.
- Material for the decision on adopting a type checker: `_register` and `_reg` declare
  `registry: dict[str, BaseRegisteredFunction[T]]`, while the call sites pass
  `dict[str, RegisteredFunction]`. `dict` is invariant in its value, so a strict checker rejects
  this, and no tool in the project reports it. Repairing it means making those functions generic
  over the registry rather than over the value, which changes their signatures. A dead module level
  `TypeVar` was removed from the same file: every `T` in it is a PEP 695 parameter that shadowed it,
  and it declared constraints that therefore applied to nothing.
- A configuration error raised while a node is built escapes `sart_engine`, because nodes are built
  before the protected section. ADR 001 owns this.
- A registered function whose parameters are all injected cannot be constructed, which makes
  `save_paths_to_deque` and the first node of `examples/colect_file_info_workflow.json` unusable.
  Guards work around it by declaring their injected parameters to the argument check; actions do
  not.
- Parameter resolution is the one thing a guard genuinely needs from the state, and it is still done
  by `StateModel.set_parameters`, so the guard class holds the state even though the guard function
  does not. Two ways out, neither decided: the engine resolves every parameter before anything is
  called; or a component receives a resolving function instead of the state.
- `ActionNodeOutput` is mutable and a guard receives it whole, so a guard can still write to the
  result it judges.
- The state mixes a journal written by the engine with a bus written by actions, and nothing
  separates the two.
- `state.error_code` is never cleared, so a run that recovers from a failure still reports it.
- `state_fields_decoder` is a JSON object hook applied to every nested dictionary, so a node named
  after a state field, now including `guard_results`, makes a saved state impossible to load.
- `set_parameters` in a node configuration has no effect, because the factory never populates it.
- `test_sart_engine` depends on files outside the repository: `C:\out\docs_pdf\...`, `C:\temp1` and
  `C:\temp2`. It passes only on the machine where those exist.

## Next steps

1. Merge into `development` and set ADR 002 to Accepted, then update `docs/architecture/overview.md`.
2. Take ADR 001 on the exception architecture to implementation, starting from the argument check
   that raises where ADR 002 expects a value.
3. Decide how data passes between nodes, as ADR 003.
4. Make `test_sart_engine` independent of files outside the repository.
5. Revisit adopting a type checker as its own ADR. The invariance problem recorded above is the first
   concrete case where a checker would have caught something no other tool reports.

## References

- Branch: `feature/adr_002-node-composition`.
- ADR: [002 node composition](../adr/adr-002-node-composition.md), Implementing.
