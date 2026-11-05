# Session 2026-11-05-implementation-1

## Type
`implementation`

## Goal
Let the node that follows an `llm` call in the same run read the facts of that call — the provider, the
model requested, the model the server reported, the status, the error class and the token counts —
through a parameter the `llm` node names, as the `payment-reconciliation` project asked.

## Completion criteria
- The `llm` action accepts an optional `save_call_as`: the name of a parameter the facts of the call
  are written to as a dictionary `{provider, model_requested, model_answered, status, error_class,
  usage: {prompt_tokens, completion_tokens}}`, an empty fact as `null` and `usage` always an object.
- The facts are written on every way out of the node: an adapter that raised, a classified failure,
  `llm_record_failed`, `llm_answer_invalid` and a success; a retry or a later visit overwrites them.
- A `save_call_as` that is not a non-empty string, or that names a parameter of the `answer`
  declaration, is a configuration error of the node at build time.
- The `details` of the record of the visit gain `model_requested`; `model` keeps its meaning.
- Tests on the `fake` adapter cover each path, the overwrite on a retry, the build-time refusals, a
  function in the next node reading the dictionary by a `param.` reference, and the node behind a
  failure transition reading the model requested.
- `README.md` and `docs/architecture/overview.md` describe the option and the record field.
- `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- No new ADR: the option writes to the bus through `param_writes` as ADR 006 already allows, and
  accepted ADR 014 and ADR 021 are not edited.
- The meaning of `model` in the record details is not changed.
- The time of a call is not measured.
- No history of the facts per visit or attempt; the last attempt of a visit is what is kept.
- The walkthroughs in `examples/` and the shipped templates are not changed.

## Status
`completed`

## Result
- `LlmAction` reads the optional `save_call_as`, refuses at build time an empty name and a name the
  `answer` declaration binds (a name that is not a string is refused by the shared parameter check),
  and adds the facts of the call as a `SET` write with overwrite allowed on all five ways out of the
  node. The help surface lists the option and a note of the node describes it.
- The facts are `{provider, model_requested, model_answered, status, error_class, usage}`: every key
  present, `usage` always an object of two counts, an unknown fact `null`. A failed call has
  `model_answered: null` whatever the adapter reported beside its failure; a reply the declaration
  refused is an answered call with `error_class: null`.
- The `details` of the record gain `model_requested`; `model` is computed as before.
- Tests: the action suite covers each way out of the node, the model of the node as the model
  requested, the requested and the reported model kept apart, null counts, the overwrite flag and the
  three build-time refusals; the run suite covers a function in the next node reading the dictionary
  by `param.`, the node behind a failure transition reading the model requested, and a retry leaving
  the facts of its last attempt beside one record per call.
- `README.md` ("What a call leaves behind") and `docs/architecture/overview.md` (the audit paragraph)
  describe the option and the record field; the README sentence that called `model` the model that
  actually answered now says it falls back to the one requested.
- Run: `uv run pytest` (880 passed), `uv run ruff check .`, `uv run ruff format --check .`.
- Not run: a call against a live model server; a run of the project's definition at its site.

## Decisions
- No ADR: the option writes to the bus through `param_writes`, which ADR 006 allows; the records stay
  the audit of every call as accepted ADR 014 §4 and ADR 021 decide, and neither is edited. The
  artifact alternative was rejected: a failed call cannot be relied on to leave a file, and a file per
  call turns the artifact registry into the log ADR 021 alternative C rejected.
- `model_requested` is added to the record details rather than changing what `model` means, so a
  reader of `show-records` is not broken and the record never knows less about a call than the
  parameter does.
- The time of a call is not measured: it would be a new fact for the records too, and the project
  measures it meanwhile.

## Open questions
- `model_answered` of an answered call is what the adapter reports, and `openai_compatible` and
  `ollama_systemone` report the requested model when the server names none; telling the two apart
  would change the adapters, not the action.

## Next steps
1. Answer the `payment-reconciliation` project with the commit of the merge, the contract of
   `save_call_as` and what to check after the pin moves.
2. Decide whether an adapter should report no model when the server names none, if the project needs
   `model_answered` to be the server's word only.

## References
- Branch: `feature/llm-call-facts-parameter`
- ADR 006, ADR 014 (§4), ADR 021 (§1, §2)
- Changed: `src/workflow_engine/actions/action_llm.py`, `tests/test_adr014_llm_action.py`,
  `tests/test_adr014_llm_e2e.py`, `README.md`, `docs/architecture/overview.md`
