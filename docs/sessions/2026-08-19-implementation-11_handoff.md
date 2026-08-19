# Session note

## Type
implementation

## Goal
Build the interactive exchange of ADR 013: an `ask` node that pauses the run with a machine-readable
question, and a `resume --answer` that binds a typed, validated answer through the node's guards.

## Completion criteria
1. A core `ask` action pauses the run, journals `workflow_paused_interactive` and reaches the caller
   as a `question` block in the command result with exit code `2`.
2. `resume --answer <json>` / `--answer-file <path>` binds a declared answer, journals
   `interactive_answered`, and routes through the node's transitions; a `failure` answer carries its
   error code into the normal retry machinery.
3. Every refusal rule of ADR 013 §5 exits `4`, applies nothing and journals nothing.
4. `inputs` and `answer` share one declaration validator, and one codec-decoding entry point serves
   both the `--input` string transport and an already-typed JSON value.
5. `pytest` and `ruff` pass from the command line, with new tests covering the exchange end to end.
6. `README.md`, `docs/architecture/overview.md` and an example workflow describe the delivered state.

## Scope boundaries
- No `escalate` status, no `audience` hint, no flag transport for the answer (ADR 013 alternatives E
  and F): they were decided against and are not built "just in case".
- ADR 014 is not started; the answer declaration is built here and reused there later.
- Reopening a `FAILED` session, retry/backoff and an in-graph budget checkpoint stay out (ADR 013 §7
  and the recovery note).
- The ADR status stays `Implementing`; it is frozen on `development` after the merge.

## Status
completed

## Result
All six criteria are met. The exchange runs end to end through the installed CLI: `run` stops at an
`ask` node with exit code `2` and a `question` block, `resume --answer` binds the declared values and
carries the run to completion, and every refusal rule exits `4` with a byte-identical state file. New
code: `answers.py` (the answer document and the published question block), `actions/action_ask.py`
(the `ask` action), `AnswerContract` on the presentation, `WorkflowAnswerError`, two session event
codes, two `resume` options, and `examples/approve-and-copy.json`.

Verified from the command line: `uv run ruff format .`, `uv run ruff check .` (clean) and
`uv run pytest` — 335 passed, up from 276; the 59 new tests are the three `test_adr013_*` modules.

## Decisions
Recorded in full in the ADR change log entry of 2026-08-19; the six that are contract, in short:

1. **The declaration and the error catalogue are one `AnswerContract`, not `PresentResponse.errors`.**
   That field states what actually failed, and a catalogue in it is the defect
   `fix/successful-run-reports-errors` removed. The engine reads the contract through
   `BaseInteractiveAction.answer_contract()`, so it validates an answer without knowing the action.
2. **`ActionNodeOutput.from_args` and the `output` parameter of `start_workflow` are removed, not
   reused** as the ADR's implementation notes suggested. Nothing called them, and `from_args` read
   `args.input`, which ADR 012 gave a different meaning; `answer` takes their place.
3. **A `failure` answer carries no `values`,** and unknown top-level fields are refused: a
   half-answer is refused rather than silently dropped.
4. **The `SET` writes of an answer allow overwriting,** because a question asked again in a loop
   answers the same names.
5. **`answer` is a required key of an `ask` node,** with `[]` for a question that binds nothing and
   is routed by its answer text.
6. **The published block names the generic code as `generic_error_code`,** so a caller learns
   `answer_failed` from the question rather than from the ADR.

## Open questions
Two defects found while building the example, both older than this session and both out of its scope:

- `file_exists_arg_validator` rejects a `pathlib.Path` argument as "not a 'str'", so an input declared
  with `type: Path` cannot feed `file_size_human`, `copy_file` or their kin, even though each does
  `Path(...)` on the value immediately. `examples/approve-and-copy.json` therefore declares its two
  path inputs untyped. Worth a small `fix/` branch.
- `ActionParameter.source_node_id` of a `param_writes` value records the **next** node, not the
  producer: `StateModel.update` moves `current_node_id` in `_update_stats` before it applies the
  writes. It affects every function that writes parameters, not only an answer.

## Next steps
1. Merge `feature/adr_013-interactive-exchange` into `development`, update the three registries, and
   check the ADR 013 freeze gate; the status field and the registry row are edited there.
2. Refine ADR 014 in Draft against the delivered answer declaration, which it reuses.
3. Open the two `fix/` branches for the defects above, and the still-open atomic `state.json` write
   (recovery note (c)).
4. Decide the text interpolation question (ADR 012 deferred §1, ADR 014 open point 1): the example
   shows the cost, a reference resolves as a whole value, so "here is the result, approve?" needs a
   node that composes the sentence first.

## References
- ADR: `docs/adr/adr-013-interactive-exchange-contract.md`
- Branch: `feature/adr_013-interactive-exchange`
- Previous session: `2026-08-19-architecture-2_handoff.md`
- Notes this touches: `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` (friction 1),
  `docs/architecture/notes/2026-08-19-node-save-as-redundancy.md` (an `ask` node names its values)
