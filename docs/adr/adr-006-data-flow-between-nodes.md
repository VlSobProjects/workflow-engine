# ADR 006: Data flow between nodes

## Status
Draft

## Active branch
None

## Context

The engine can run a linear workflow. It cannot yet be trusted with a multi step branching workflow,
because there is no contract for how data travels from one node to the next.

Facts from the current code:

1. `StateModel` mixes two different things under one object:
   - a **journal** written by the engine: `outputs`, `errors`, `error_code`, `visit_counters`,
     `attempt_counters`, `guard_results`, `nodes_visited`;
   - a **bus** written by actions: `params`.
2. The only value that crosses a node boundary by contract is `ActionNodeOutput.output_text`, a string.
   `save_as` stores that string as a parameter, so every typed value degrades to text at the boundary.
3. `ActionNodeOutput.parameters` is a second, undocumented channel. `update_parameters` copies it from the
   previous output into the next one, and `for_each_node` reads it. It is never persisted, so anything
   that travels this way is lost when a session is resumed.
4. Actions mutate parameters in place: `FunctionsAction` appends to a list obtained through `get_param`,
   `PopFromQueue` pops from a `deque` in the state. These changes bypass `save_as` and leave no trace in
   the journal.
5. `StateModel.artifacts` exists and is persisted, but nothing ever writes to it. `create_artifact` writes
   into `work_dir/artifacts` and returns the path as `output_text`.
6. The actions needed for the branching scenario are not registered at all: `FunctionsAction`,
   `PopFromQueue` and `CreateArtifactActionWithContent` carry no `@register_action()`. The example
   `examples/colect_file_info_workflow.json` therefore cannot run, and it also passes `param_name` where
   `save_paths_to_deque` expects `deque_param_name`.

The acceptance scenario for this decision is deliberately concrete: scan a folder, push its entries into a
queue, loop over the queue, branch on file versus folder, collect per file information, and write a sorted
table into an artifact.

This is a single developer project. The decision should be the smallest contract that makes such a
workflow work, survive a resume, and be debuggable. It is not an attempt to design a general data flow
engine.

## Decision

Not decided yet. This draft states the questions that the discussion has to answer.

The proposed direction, to be confirmed or rejected in discussion:

- The journal belongs to the engine and is read-only for actions.
- `params` is the only bus, it is persisted, and it is the only channel between non adjacent nodes.
- `ActionNodeOutput.parameters` is removed as a parallel channel.
- Collections in `params` are manipulated only through dedicated actions, never mutated by arbitrary code.
- An artifact is a file under `work_dir/artifacts` that is registered in `state.artifacts`.

## Questions to settle

### Q1. Who may write to `params`?
Options: only the engine through `save_as`; or actions as well, through an explicit API.
Trade-off: engine only is easier to reason about and keeps the journal truthful, but queue and accumulator
actions then need a way to publish their result other than a single string.

### Q2. Does `ActionNodeOutput.parameters` survive?
Options: remove it and route everything through `params`; keep it as a short lived channel between two
adjacent nodes only, and document that it is not persisted.
Trade-off: removing it breaks `for_each_node` as written; keeping it means a resume can silently behave
differently from a straight run. Leaning to removal.

### Q3. Can a node publish a typed value, or only text?
Options: `output_text` stays the only carrier and typed values live only in `params`; or
`ActionNodeOutput` gains an explicit typed result that `save_as` stores through a codec.
Trade-off: text only keeps the output contract trivial but forces string parsing in the scenario above
(file size, timestamps, table rows).

### Q4. How are collections handled?
Options: in-place mutation of a collection parameter, as today; or explicit operations
(`queue_push`, `queue_pop`, `list_append`) that read a parameter and write it back through the same API as
any other parameter.
Trade-off: in-place mutation is shorter but invisible to the journal and impossible to trace when a loop
misbehaves.

### Q5. Do parameters need a namespace?
Options: keep one flat namespace keyed by `save_as`; or qualify parameters by the node that produced them.
Trade-off: flat is simpler and matches `param.` references in guards; qualified prevents silent overwrites
in loops. Leaning to flat, with an explicit rule about overwriting.

### Q6. What is an artifact and who registers it?
Options: any file the workflow produced under `work_dir/artifacts`, registered in `state.artifacts` by the
action that created it; or drop `state.artifacts` entirely and treat artifacts as ordinary files.
Trade-off: registering makes the result of a run discoverable without walking the filesystem; dropping it
removes an unused field. One of the two has to happen, the current half state must not stay.

### Q7. What may guards read?
Guards currently read the state only through resolved `param.` and `output.` references. Confirm that this
stays, and that guards never see the collections themselves.

### Q8. Loop termination.
`flow_budget` and `nodes_visited` are carried in the state but never enforce anything; only
`max_attempts` per node does. Decide whether a global budget belongs in this ADR or in a separate one on
retry and termination policy. Leaning to a separate ADR.

### Q9. Which of the existing actions are part of the contract?
`FunctionsAction`, `PopFromQueue`, `CreateArtifactActionWithContent`, `ForEachOutputParameterNode` and
`StopOnError` are in the tree but partly unregistered and untested. Each has to be registered and covered,
reshaped, or deleted. Deleting what the scenario does not need is an acceptable outcome.

## Alternatives considered

### A. Explicit split: engine journal, action bus
The engine owns the journal and writes it; actions publish results into `params` through one API.
Pros: one place to look when a run misbehaves; resume behaves like a straight run.
Cons: existing actions that mutate collections must be rewritten.

### B. No bus: everything flows through outputs
Every node consumes the previous output and produces the next one; nothing accumulates in the state.
Pros: simplest possible contract.
Cons: the acceptance scenario needs an accumulator and a queue that outlive a single transition, so this
would push that state into artifacts or into node configuration. Likely too restrictive.

### C. Formalize the status quo
Declare that actions may read and write any part of the state.
Pros: no code changes.
Cons: the journal cannot be trusted, and the second channel keeps making resume differ from a straight
run. Rejected unless the discussion shows the cost of A is too high.

## Consequences

To be written once the decision is made. Expected to touch `StateModel`, `ActionNodeOutput`, the
collection actions, the artifact action and the example workflows.

## Related ADRs

- ADR 002 node composition (Accepted): defines what a node is and how guards read data.
- ADR 003 persistence boundary and run workspace (Accepted): defines `work_dir`, where artifacts live.
- ADR 004 session bootstrap and configuration snapshot (Accepted): defines the session workspace layout.

## Implementation notes

Acceptance scenario, to be delivered as an example workflow and an end to end test:

1. Scan a folder and push its entries into a queue parameter.
2. Loop: pop one entry, branch on file versus folder, and push folder contents back into the queue.
3. For a file, collect its attributes and append them to an accumulator.
4. When the queue is empty, sort the accumulated rows by file type and write a table into an artifact.
5. Resume the same workflow mid loop and reach the same result.

Whether step 5 needs an interactive node, or a second engine instance is enough, is part of the
discussion.

## Change log

- Initial draft created to open the data flow discussion, with the folder scan scenario as the acceptance
  case.
