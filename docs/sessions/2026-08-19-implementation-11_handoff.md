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
All six completion criteria of this session are met. That is the implementation report of the
session, not the acceptance of the decision: ADR 013 is accepted against the freeze gate of
`docs/adr/process.md`, at the merge into `development`, and stays `Implementing` until then.

The exchange runs end to end through the installed CLI: `run` stops at an `ask` node with exit code
`2` and a `question` block, `resume --answer` binds the declared values and carries the run to
completion, and every refusal rule exits `4` with a byte-identical state file. New code: `answers.py`
(the answer document and the published question block), `actions/action_ask.py` (the `ask` action),
`AnswerContract` on the presentation, `WorkflowAnswerError`, two session event codes, two `resume`
options, and `examples/approve-and-copy.json`.

Verified from the command line: `uv run ruff format .`, `uv run ruff check .` (clean) and
`uv run pytest` — 335 passed, up from 276; the 59 new tests are the three `test_adr013_*` modules.

An architectural review of the result found no blocking defect and three places where the boundary
between the engine's internal shapes and the published contract is held by convention rather than by
the code. They are recorded as
`docs/architecture/notes/2026-08-19-interactive-exchange-publishing-boundary.md`, not fixed here:
each is a decision of its own size, and two of them are ADR-sized.

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
Three from the review, all in
`docs/architecture/notes/2026-08-19-interactive-exchange-publishing-boundary.md`:

- **`PresentResponse` still looks publishable.** It keeps `submit`, `expected_input`, `def_errors`,
  `SubmitResult` and `SubmitStatus`, which the declared answer replaced; ADR 013 removed the two
  field defaults and no more. The boundary is currently one function, `question_block`, so the
  standing risk is that someone later just serializes the dataclass — alternative G, which the ADR
  rejected. Technical debt, not a blocker: marking the class internal and deleting the unused
  symbols is cheap, splitting it into a presentation and separate reports is an ADR.
- **`actor` is a label, not an identity.** Free text, supplied by the caller, verified by nothing.
  Correct for the audit story of §9, wrong the moment a guard, an export filter or a policy branches
  on it. The project has to state which of the two it is before the first such use.
- **The published question carries no version.** `data.question` is consumed by programs; the ADR
  009 help payload has `contract_version` and the command result has none. Worth deciding once for
  every machine-readable payload rather than per block.

The note also records the one invariant the engine cannot enforce alone: §5 keeps a refused answer
out of the journal, but a wrapper or transport that writes its own audit trail would put it back.

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
2. The cheap half of review point 1, as its own small branch: state in the class docstring that
   `PresentResponse` is internal and `question_block` is the only publisher, and delete `def_errors`,
   `SubmitResult`, `SubmitStatus` and the two fields the declared answer replaced. Splitting the
   class is the expensive half and needs an ADR; do not start it in the same branch.
3. Refine ADR 014 in Draft against the delivered answer declaration, which it reuses — and decide
   there whether the payload it publishes carries a version, together with review point 3 rather than
   separately.
4. Answer review point 2 before anything reads `actor`: either write into the contract that it is an
   audit label no component may branch on, or open an ADR for identity, which this engine has no
   notion of today.
5. Open the two `fix/` branches for the defects above, and the still-open atomic `state.json` write
   (recovery note (c)).
6. Decide the text interpolation question (ADR 012 deferred §1, ADR 014 open point 1): the example
   shows the cost, a reference resolves as a whole value, so "here is the result, approve?" needs a
   node that composes the sentence first.

## References
- ADR: `docs/adr/adr-013-interactive-exchange-contract.md`
- Branch: `feature/adr_013-interactive-exchange`
- Previous session: `2026-08-19-architecture-2_handoff.md`
- Note opened: `docs/architecture/notes/2026-08-19-interactive-exchange-publishing-boundary.md`
- Notes this touches: `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` (friction 1),
  `docs/architecture/notes/2026-08-19-node-save-as-redundancy.md` (an `ask` node names its values)
