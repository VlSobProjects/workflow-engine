# Session 2026-11-02-investigation-1

## Type
`investigation`

## Goal
Establish against a live Ollama server whether the context window of a decision model can be set by a
load the `ollama_systemone` adapter performs, and whether the server then reports that context.

## Completion criteria
- A load-only request with a context option is sent to the server for a decision model, on the
  decision endpoint and on the native generate endpoint, and whether each is accepted is recorded.
- After an accepted load, the context the server reports for the loaded model is read and compared
  with the one requested.
- Whether a decision call made after such a load runs on the loaded model with that context, or makes
  the server load it again, is recorded.
- The outcome is stated as one of the two branches of the preceding session's next step 2: the load
  in the provider block under ADR 014 §2, or the answer that the context is the operator's model
  variant and the project's bound on the questions of one call.

## Scope boundaries
- No code changes: the implementation of the load is the next session, under ADR 014 §2.
- No reply to the `payment-reconciliation` project and no letter on the exchange desk.
- The body of a refused call in the record of the run is not touched.
- Only the server version and the models already present are used; nothing is pulled or upgraded.

## Status
`completed`

## Result
Measured on Ollama 0.40.12 with the decision model `d3:2b`, whose model file sets `num_ctx` and
`num_batch` to 4096.

- No load-only request exists for a decision model. The decision endpoint refuses a body without
  questions with a 400, and the native generate and chat endpoints refuse the model as not supporting
  them; nothing is loaded in either case. A request to the generate endpoint with `keep_alive: 0` does
  unload a decision model, so the release the adapter performs in `finalize` holds.
- A context option on a decision call is accepted and ignored: `options.num_ctx`, and `num_ctx` or
  `context_length` at the top level of the body, all answer 200 and leave the model at the context of
  its model file.
- The context of a decision model is set only by a model variant whose model file carries the
  parameter, and the running-models endpoint then reports that `num_ctx` as `context_length`.
- The bound on the input of one decision call is the smaller of `num_ctx` and `num_batch`, not
  `num_ctx` alone. A variant with `num_ctx` 8192 and the inherited `num_batch` 4096 reports 8192 and
  still refuses above about 4100 input tokens, exactly like the base model; a variant with both at 8192
  answers 8150 input tokens; a variant with `num_ctx` 2048 refuses above 2048. The reported
  `context_length` therefore overstates the bound whenever `num_batch` is the smaller of the two.
- The server refuses an oversized decision call with a 400 in two wordings, `the prompt is longer than
  the context length currently available to the model` and `input (N tokens) is larger than the max
  context size (M tokens)`, besides the 500 `Context size has been exceeded.` the preceding session
  covered. The shared status rule classes both 400 wordings as `context_overflow` as it stands.
- The variants made for the probes were removed and the server was left with no model loaded.

## Decisions
- The second branch of the preceding session's next step 2 holds: no load is implemented in
  `ollama_systemone`. The context of a decision model is the operator's model variant, with
  `num_batch` raised together with `num_ctx`, and the project bounds the size of the state and the
  questions of one call to the smaller of the two.

## Open questions
- Whether the adapter's operator description should state the `num_batch` half of the bound; it is a
  documentation change of the provider package, outside this session.

## Next steps
1. Answer the `payment-reconciliation` project on the third gap: the context of a decision model is
   set by a model variant with `num_ctx` and `num_batch` together, the bound of one call is the smaller
   of the two, and an overflow arrives as `context_overflow`.
2. A documentation change to the operator description of `ollama_systemone` naming the bound, if the
   owner wants it.

## References
- Branch: `docs/decision-model-context-probe`
- Preceding session: `2026-11-02-implementation-1`
- ADR 014 (§2)
