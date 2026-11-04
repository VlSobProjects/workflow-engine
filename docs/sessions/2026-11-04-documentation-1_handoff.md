# Session 2026-11-04-documentation-1

## Type
`documentation`

## Goal
State in the operator description of `ollama_systemone` how the context of a decision model is set and
what bounds the input of one call.

## Completion criteria
- The `notes` of the `ollama_systemone` registration carry one note: the context is the model file's,
  a larger one is a model variant raising `num_ctx` and `num_batch` together, the input of one call is
  bounded by the smaller of the two, and an input above it comes back as `context_overflow`.
- `help-component --component-type providers` shows the note.
- `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- No behaviour change: only the text the adapter reports to the operator.
- `README.md`, `docs/architecture/overview.md` and the module docstring are not touched.
- Whether the provider contract lets an adapter report an option it could not apply is not decided here.

## Status
`completed`

## Result
- A fifth note in the `ollama_systemone` registration states that the context is the model file's, that
  a larger one is a model variant raising `num_ctx` and `num_batch` together, that the input of one call
  is bounded by the smaller of the two so the reported `context_length` can overstate it, and that an
  input above the bound comes back as `context_overflow`.
- `help-component --component-type providers --component-name ollama_systemone` shows the note.
- `uv run pytest`: 862 passed. `uv run ruff check .`: all checks passed.

## Decisions
- The bound is stated once, in the adapter's operator notes, which `help-component` reports. `README.md`
  keeps its general paragraph on the adapter without configuration detail.
- The branch is `docs/`: the change is text the operator reads, with no behaviour change.

## Open questions
- Whether the provider contract should let an adapter report a call option it could not apply, raised
  by the `payment-reconciliation` project and not decided by the engine.

## Next steps
1. If the project raises it, an architecture discussion on letting an adapter report a call option it
   could not apply.

## References
- Branch: `docs/ollama-systemone-context-bound`
- Preceding session: `2026-11-02-investigation-1`
- ADR 014 (§2)
- Changed: `src/workflow_engine_providers/ollama_systemone.py`
