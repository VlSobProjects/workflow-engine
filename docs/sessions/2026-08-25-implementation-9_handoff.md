# Session 2026-08-25-implementation-9

## Type
implementation

## Goal
Close the two-provider residency gap the live rehearsal confirmed: give the `lmstudio` adapter a
per-server residency registry shared by every provider block of one run, so a load is a swap across
blocks and a block's `load_config` reaches the model it asks for.

## Completion criteria
- A load releases every instance the run holds on that server, whichever provider block loaded it,
  so two blocks on one server no longer sit on two resident models at once.
- A request for a model the run already holds reuses the resident instance when the requesting
  block's `load_config` matches what it was loaded with, and reloads it under the requesting
  block's settings when it differs.
- An instance the run did not load stays untouched by default; `release_foreign: true` widens to
  clearing the whole server once, before the run's first residency check on it.
- Every rule is covered by a test against the scripted server that holds real residency, and
  `uv run pytest` and `uv run ruff check .` run clean.
- The operator-facing description of the adapter — its registered notes and the example
  configuration — says what the new behaviour is.

## Scope boundaries
- The `openai_compatible` parent is not touched: nothing product-specific enters a protocol adapter.
- The engine, the provider seat and the `llm` action are not touched; this is adapter code.
- The three open questions of `2026-08-25-implementation-8` — a per-node timeout, the deterministic
  invalid-reply retry, where the small-model pattern is documented — stay open.
- ADR 014 is frozen and is not edited: this closes a question its §2 left open without contradicting
  it, and the closing is recorded here.

## Status
`completed`

## Result
The adapter's residency memory moved off the adapter object into a module-level registry keyed by
the model API root: per server, what the run holds there, each instance recorded with the block that
loaded it, its model and the `load_config` it was loaded with, plus whether the widened permission
has already emptied that server. All four rules of the design hold and are covered by twelve new
tests against the scripted server that keeps real residency; the suite is 820 passing.

- **The swap crosses provider blocks.** A load releases what any block of the run holds on that
  server, so a run holds one model at a time on one machine — the rule the adapter always stated and
  the live rehearsal measured it breaking.
- **A block's `load_config` reaches the server.** A resident instance answers a call when the run
  did not load it (someone else's model, used as it stands) or when it was loaded with exactly what
  the asking block declares. A block declaring another window gets the model loaded again under its
  own settings, which is the whole reason a second block names one model.
- **`release_foreign: true` empties the server once**, before the run's first residency check on it,
  and keeps its former meaning of allowing a foreign instance to be unloaded after a call. An
  unreadable listing leaves the permission unspent; a model loaded while the run works is not swept
  up; one clearing serves every block of the run; the permission is fresh again for the next run.
- **Each block still finalizes only what it loaded.** Every seated block is finalized, so between
  them the run's holdings are covered exactly once, and a block whose model another block swapped
  away finalizes quietly instead of reporting a failure to release something already gone.
- Operator-facing text carries the change: the registered notes and metadata of the adapter, the
  comments of `example_config.json`, and the one README sentence that said the adapter releases what
  *it* loaded rather than what the *run* loaded.

## Decisions
1. **Residency is counted per server, not per provider block, and the registry is module state.**
   The alternative — passing a shared object into every adapter instance — would have needed the
   seat to know that two blocks name one machine, which is a fact about the machine and belongs to
   the adapter that speaks to it. Two blocks are the same server when their model API roots are the
   same string: the adapter cannot know that two spellings of a URL reach one machine, so a block
   declaring `api_base_url` declares which residency it joins.
2. **The widened `release_foreign` clears before the first residency *check*, not before the first
   *load*.** Clearing before the load would leave the case the option exists for unfixed: a foreign
   instance of the very model the run asks for is what the check would reuse, with someone else's
   window and with the memory still spent on whatever sits beside it.
3. **The permission is spent per run, and the run ends at `finalize`.** The mark lives on the server
   entry, and the entry is dropped when the run holds nothing there any more, so the next run in the
   same process empties the server again instead of inheriting a clearing it never performed. A
   clearing whose listing could not be read is not marked as spent, because one unreachable moment
   must not cancel the permission for the rest of the run.
4. **ADR 014 stays frozen and unedited.** Its §2 left "a re-load to change the window of a resident
   model" open "until a scenario needs two windows for one model"; the rehearsal is that scenario,
   and closing the question does not contradict the ADR's reasoning, whose subject is a model
   *someone else* loaded. Writing the closing into the frozen text would be a superseding decision,
   which this defect fix is not.

## Open questions
- Whether `release_foreign` is still the right shape now that it means two things — a permission to
  unload a foreign instance and an up-front clearing of the machine. It remains the blunt instrument
  the residency session already flagged.
- Whether a run should be able to hold two models on one server deliberately, when a machine is
  large enough for both and a flow alternates between them. Today the swap is unconditional, and the
  rehearsal gave no case for the alternative.
- The three questions of `2026-08-25-implementation-8` are untouched: a node-scoped call timeout, a
  retry route that distinguishes a deterministic `llm_answer_invalid` from a transient one, and
  where the "one-word answer plus functions" small-model pattern is documented.

## Next steps
1. Roadmap step 14: the data-generation discussion, then the generators for the dataset variants and
   the drift-B experiment protocol.
2. Roadmap step 15: build the exit scenario by hand on the generated variants and run the drift-B
   measurement that closes phase 2.

## References
- Branch: `fix/lmstudio-residency-registry`
- ADRs: ADR 014 (`llm` node, provider adapters), §2 for the residency rules — read, not edited
- Documents changed: `README.md` (one sentence), this note
- Code changed: `src/workflow_engine_providers/lmstudio.py`,
  `src/workflow_engine_providers/example_config.json`, `tests/test_adr014_lmstudio_adapter.py`
