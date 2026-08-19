# Is the node level `save_as` still needed next to `output.<node_id>`?

- **Date:** 2026-08-19
- **Trigger:** review of the `FunctionAction` operator metadata during
  `2026-08-19-implementation-3` (the dead `BaseAction.save_as` field), and the user's observation
  that `save_as` predates the typed parameter channel and may have lost its purpose
- **Status:** open
- **Affected:** ADR 006 (data flow between nodes), ADR 009 (operator help contract)

## The observation

`save_as` is a node level key: the engine reads it from the node configuration
(`models/node.py`, `engine.py`) and, when the action produced no error code, copies the node's
output text into `state.params` under that name (`models/state.py`, `_update_cur_node`).

The same text is already stored unconditionally in `state.outputs[node_id]` in the same method, and
`output.<node_id>` references resolve against it. So `save_as` writes a second copy of a value the
state already holds, under a different name. That is the redundancy.

## Why it is not a free removal today

1. **No other channel gives the function's output a name chosen by the workflow author.** The typed
   `param_writes` channel is used by functions that take the target parameter name as an argument
   (`init_list_param` and its kin). A general function such as `copy_file` writes no parameter; its
   result reaches the state only as the node output. Replacing `save_as` for those would mean adding
   a "target parameter name" argument to every such function, which is a larger contract change than
   removing the key.
2. **The name is decoupled from the node id.** `param.copied_path` names the value; `output.COPY_FILE`
   names the producer. When two alternative branches produce the same logical value, `save_as` lets
   both write one name and lets the consumer stay ignorant of which branch ran. Output references
   cannot express that.
3. **The value is untyped either way.** `save_as` stores `output_text`, always a string, so nothing
   of the codec typing of the parameter bus is gained or lost by the choice.

## Options if this is taken up

- **Keep as is.** Cost: one config key that duplicates a channel, and a value that exists twice in
  every persisted state.
- **Retire `save_as`, rewrite the examples on `output.<node_id>`.** Cost: a breaking change of the
  workflow definition contract, plus the loss of author-chosen naming in point 2 unless something
  replaces it.
- **Retire `save_as` and generalize the parameter write.** For example a node level `write_output_to`
  handled by the engine, or a documented convention that functions whose result is meant to be reused
  declare it through `param_writes`. This keeps the naming and removes the duplication, at the cost of
  designing the replacement.

## What this note does not decide

Nothing. `save_as` stays in phase 1: it is used by `examples/flatten-copy-tree.json`, by the engine
test fixture, and by the operator help of four actions. Any change here is a change of the workflow
definition contract and belongs in an ADR after the release.
