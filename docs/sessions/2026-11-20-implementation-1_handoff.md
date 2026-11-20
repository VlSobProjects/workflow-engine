# Session 2026-11-20-implementation-1

## Type
`implementation`

## Goal
Let the record of an `llm` visit say whether the adapter reported the model that answered, by adding
`model_answered` to its `details`, as the `llm-test-bench` project's letter EX-38 (2026-11-19, the
environment a model call ran in) needs; the existing `model` key keeps its meaning.

## Completion criteria
- The `details` of every `llm` visit carry `model_answered`: the model the adapter reported, `null`
  where it reported none or the call failed — the same rule as the `save_call_as` facts.
- `model` and every other key of the `details` keep their documented meaning.
- Tests pin `model_answered` for a reported model, an unreported one and a failed call.
- `README.md` and `docs/architecture/overview.md` describe the new key.
- `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- No change to the adapter contract (`ProviderReply`), to any adapter or to the record shape outside
  the `llm` details; no ADR.
- The rest of EX-38 (the options sent, the metrics a provider reports, the model's digest,
  quantization and context length) and EX-39 are not implemented; they wait for an ADR.
- The answers on the exchange desk are written after the merge, as drafts.

## Status
`completed`

## Result
- The `details` of an `llm` visit carry `model_answered`, computed by one rule shared with the
  `save_call_as` facts: the model the adapter reported, `null` where it reported none or the call
  failed. `model` keeps its documented fallback to the model requested.
- Tests pin the key for a reported model, a model the adapter did not report and a failed call; the
  end-to-end record test and the key-set test carry the new key.
- `README.md` (what a call leaves behind, the `show-records` example line) and
  `docs/architecture/overview.md` (the audit paragraph) describe the key.
- `uv run pytest` (883 passed), `uv run ruff check .` and `uv run ruff format --check .` pass.

## Decisions
- The fallback in `model` was confirmed as a documented contract, not a defect; changing its meaning
  was rejected because it would break readers of the records. The fact is added beside it instead.
- No ADR: the `details` member of a record is open per action kind (ADR 021 §1), and the key adds a
  fact the adapter contract already carries.
- Of EX-38, the options sent and the metrics a provider reports are to go to an ADR: an open member of
  the reply, filled by each adapter under documented names and never read by the core, with the
  normalization across providers left to `llm-test-bench`. The model's digest, quantization and
  context length are reached by functions an adapter package ships, from a node of the workflow.

## Open questions
- Whether the per-call wall time is measured by the engine in the same ADR as the open member.

## Next steps
1. Merge the branch into `development` and register this session.
2. Write the answers to EX-37, EX-38 and EX-39 on the desk as drafts, the one to EX-38 naming the
   merge commit; fill `What it changed` of EX-38 once its answer is released.
3. Open the ADR on the facts a provider reports about a call (the open member of the reply), after
   checking the ADR registry against general rule 11.
4. Write the `llm-test-bench` scenario in a documentation session, as the answer to EX-37 promises.
5. Open the ADR on the inputs of every visit (EX-39) when the registry allows it.

## References
- Branch: `feature/llm-record-model-answered`
- ADR 014 §4 (the call audit), ADR 021 §1 (the `details` member of a record)
- Desk letters: EX-37 (2026-11-18, llm-test-bench joins the desk), EX-38 (2026-11-19, the environment a
  model call ran in), EX-39 (2026-11-19, the value written at every visit of a node)
