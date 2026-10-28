# Session 2026-10-28-implementation-1

## Type
`implementation`

## Goal
Add to the provider-adapter package an `ollama_systemone` adapter through which an `llm` node calls a
decision model over the Ollama System One API and binds the probabilities of its answers, as asked by
the payment-reconciliation project.

## Completion criteria
- A configuration that loads `workflow_engine_providers` and declares a provider block with
  `adapter: ollama_systemone` and a local `base_url`, with no hosted endpoint and no credential, seats
  the adapter.
- An `llm` node with `format: json`, one `noul` question in its call option `questions` and an answer
  declaring one `float` binds the probability of yes, from 0 to 1, as a parameter.
- Several questions about one state are asked in one call; a `choice` or `score` answer binds as a
  dictionary carrying what the server returned.
- A failed call is one of the six error classes of ADR 014 §5, routable by the node.
- The adapter releases at the end of a run, except on a pause, the models the run brought onto the
  server, and never a model the server held before the run first looked at it.
- The adapter is covered by tests against a scripted HTTP server and listed on the help surface.
- One manual run against a small local decision model binds a probability; what it showed about the
  release and the refusal of an oversized input is recorded here.
- `README.md`, the package's `example_config.json` and `docs/architecture/overview.md` say what the
  change made inaccurate; `uv run pytest` and `uv run ruff check .` are clean.

## Scope boundaries
- No change to the core: the provider contract, the `llm` action and the guards stay as they are.
- No threshold guard: a threshold on a probability is routed by the consumer's own validator
  (scenario `payment-reconciliation`, open decision 2).
- No change to the `openai_compatible` and `lmstudio` adapters beyond reusing their public helpers.
- Images, which the API accepts, are not carried: the `llm` node carries text only.
- Which questions are asked, of which model and with which threshold is the consumer's to decide.

## Status
`completed`

## Result
- `ollama_systemone` ships in `workflow_engine_providers` and registers with the package. It sends the
  resolved prompt as the state and the call option `questions` unread to `<base_url>/systemone`, and
  returns a JSON object of question name to answer: a number for `noul`, the server's answer object
  without its `type` for `choice` and `score`. Usage maps `input_tokens`/`output_tokens` onto the
  contract's prompt and completion counts.
- Residency follows the `lmstudio` ownership rule, counted per server: before a call the running-model
  listing is read, and a model it does not show is recorded as brought by the calling block; at the end
  of a run every outcome but `paused` releases what the block brought and the server still holds, with
  an empty-prompt generate request carrying a zero keep-alive. A model already resident is never
  released, and an unreadable listing claims nothing. `keep_alive` is resolved from the node, then the
  provider block, and sent to the server.
- Tests against a scripted server with real residency cover the request, the three answer forms,
  several questions in one call, the failure classes, the release rules, two blocks on one server and
  the `llm` node binding a `float` and a `dict`; the package's loader test lists the adapter.
- Manual check against a small multilingual decision model on a local Ollama server of the version the
  consumer runs: an `llm` node bound the probability and a `choice` answer, a pause kept the model, a
  completed run released it, and a model resident before the run was left resident.
- `README.md`, `docs/architecture/overview.md` and the package's `example_config.json` describe the
  adapter.

## Decisions
- Option A of the consumer's request: an adapter behind the existing `llm` node, the core unchanged. A
  typed decision contract in the core (option B) and a decision method beside `complete` with its own
  action were both rejected for now: each is an ADR and a core change that the consumer's one question
  type does not yet need, and a threshold on a float is already the consumer's validator (scenario
  `payment-reconciliation`, open decision 2). They return if a scenario needs questions checked at
  build time or a probability carried as a value of its own.
- No ADR: ADR 014 §2 leaves the protocol set of the adapter package to the module, and nothing in an
  accepted ADR is contradicted.
- A sibling of `openai_compatible`, not a subclass: endpoint, request and reply differ; only
  `classify_status` and `text_of` are shared.
- The adapter does not check that the model is a decision model; the server's refusal speaks, as
  `invalid_request`.
- No new overflow marker: the measured refusal of an input longer than the loaded context is a 400
  whose text carries `context length`, which the shared rule already maps to `context_overflow`; the
  server's 413 for a request over its size limits maps there by status.
- The live release works through the native generate endpoint with an empty prompt and a zero
  keep-alive, measured on a decision model.

## Open questions
- On the manual check, adding `criteria` descriptions to a `noul` question moved the probability for
  the same obvious message from about 0.92 to about 0.02. How questions are worded is the consumer's
  to measure; the engine passes them unread.

## Next steps
1. Merge `feature/ollama-systemone-adapter` into `development` and add the registry row.
2. The consumer moves its engine pin in a `chore/` branch and closes its request note.
3. Review with the user what of the consumer's implementation may come back as a general solution.

## References
- Branch: `feature/ollama-systemone-adapter`
- ADR 014 (the provider contract this adapter implements; its §2 leaves the package's protocol set to
  the module)
- Scenario `docs/architecture/scenarios/payment-reconciliation.md`
- Changed: `src/workflow_engine_providers/ollama_systemone.py`, `src/workflow_engine_providers/__init__.py`,
  `src/workflow_engine_providers/example_config.json`, `tests/test_adr014_ollama_systemone_adapter.py`,
  `tests/test_adr014_adapter_package.py`, `README.md`, `docs/architecture/overview.md`
