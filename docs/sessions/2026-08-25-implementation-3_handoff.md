# Session note: 2026-08-25 implementation 3

## Type
`implementation`

## Goal
Add the three named variants of `folder-inventory-to-csv` that ADR 014 names as its class 4
evidence — `described`, `tiered` and `chunked` — together with the generic bus components they
need, so that the `llm` node, its error classes and the provider seat are exercised by shipped
workflows rather than by tests alone.

This is the first half of session 4 of the ADR 014 arc as sized in `2026-08-24-investigation-1`.
The session was split when it was opened: the variants are carried here, and the documentation set,
the merge and the freeze gate are the closing session of the same branch,
`feature/adr_014-llm-node-and-provider-adapter`.

## Completion criteria
- Three definitions in `examples/` beside the base one, each a run of its own rather than a mode of
  one file, so a variant can be named as the evidence of a gate and executed on its own.
- `described`: a guard routes a file whose format a parameter lists to an `llm` node, and the
  description that node writes becomes a column of the same row. A file of another format keeps its
  row and says it was not described.
- `tiered`: a second `llm` step composes an optimization proposal over the accumulated table, and
  the run ends with two deliverables, the CSV table and the proposal text written by a file
  function. The describing step takes the model of the provider block and the proposal step names
  its own `model` on the node, so one definition exercises both the default and the per-node choice.
- `chunked`: a file the model refuses as too large leaves the description node under
  `context_overflow` and is described part by part through a split-and-accumulate loop — one call
  per part, the parts summarized into the one description that reaches the same column as in
  `described`.
- The components the variants need are generic bus work rather than variant-specific helpers, and
  each carries its help entry: a validator for membership of a listed collection, a function that
  reads a text file onto the bus, and a function that splits text into chunks in a deque. The
  accumulating half is the existing `init_list_param`/`append_to_param` pair, unchanged.
- Every model node records its prompt and its reply as artifacts, and the record of each visit
  carries the provider, the model and the token counts the adapter reported.
- Each variant is covered end to end through the installed CLI on the `fake` adapter, including the
  failure path it adds, so `pytest` reaches no network.
- Each variant is run by hand against a local model server, with the records of the run read back,
  and what the run measured is written into this note rather than assumed.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No documentation set: `README.md`, `docs/architecture/overview.md`, `examples/README.md`, the
  walkthrough of the example and the scenario registry row belong to the closing session of this
  branch, with the merge and the freeze gate.
- No change to the core of ADR 014: the `llm` action, the provider contract, the provider seat and
  the six error classes stay as the three preceding sessions delivered them. A variant that finds
  the surface wanting records a finding rather than changing it here.
- No change to the adapter package and no third adapter - **widened during the session, see
  decision 4**: no third adapter, but `lmstudio` gained the swap ADR 014 §2 already names,
  because the `tiered` variant could not be measured without it.
- No retry or backoff policy: a variant routes the classes it needs with the existing
  `max_attempts` allowance and nothing else.
- No second scenario document: these are named variants of one class 4 scenario.
- No prompt library and no per-model formatting; the prompts are the plain template text of the
  definitions.

## Status
`completed`

## Result
All completion criteria are met, with one scope boundary widened in the open (decision 4).

- Three definitions beside the base one, each a run of its own:
  `examples/folder-inventory-to-csv-described.json`, `-tiered.json`, `-chunked.json`. `described`
  routes a file whose MIME type a `list` input names to an `llm` node and puts what it wrote into
  the `Description` column of the same row; a file of another format, and a file that does not read
  as text, keep their row and say they were not described. `tiered` adds a second `llm` step over
  the accumulated table and a text artifact, so the run ends with two deliverables; its describing
  step names no model and takes the provider block's, its proposal step names its own on the node.
  `chunked` routes the `context_overflow` of the describing step into a split-and-accumulate loop -
  one call per part, the parts summarized into the one description that reaches the same column.
- Three generic bus components, each with its help entry: `is_output_in_collection`
  (`validators/output_function_validators.py`), `read_text_file` and `split_text_to_deque`
  (`actions/modify_param_functions.py`). The splitter counts characters and carries no library, by
  decision 1. `init_list_param` gained an optional `allow_overwrite` so an accumulator can start
  over inside a loop (decision 2); every existing call behaves exactly as before.
- Every model node declares `record: true`, so each call leaves its prompt and its reply as
  artifacts numbered by the visit and the attempt, and the record of each visit carries the
  provider, the model, the status and the token counts the adapter reported.
- 26 tests for the components (`tests/test_adr014_bus_components.py`), 12 end-to-end runs of the
  three variants through the installed CLI on the `fake` adapter, success path and added failure
  path each (`tests/test_adr014_inventory_variants.py`), and 4 for the swap
  (`tests/test_adr014_lmstudio_adapter.py`). `uv run pytest` 758 passed, `uv run ruff check .`
  clean, `uv run ruff format .` applied. No test reaches a network.

What ran by hand against the local model server, the describing model `liquid/lfm2.5-1.2b`
throughout, with the server's own listing read before and after every run:

- `described`, window 8192: three calls, 12.4 seconds, 181-222 prompt tokens each; the image row
  says it was not described, and nothing was left resident.
- `tiered`, window 8192, proposal on `mistralai/ministral-3-3b`: four calls, 68.5 and 80.2 seconds
  over two runs, the proposal call 1114 prompt tokens against 305 completion tokens, and a proposal
  a person can act on. The listing was polled once a second through the run: empty, then the small
  model alone, then the proposal model alone, then empty. The two models are never resident at
  once, which is decision 4 measured rather than argued.
- `chunked`, window 4096: the server refused the whole file with *"request (5632 tokens) exceeds the
  available context size (4096 tokens)"*, which arrived as `context_overflow`; the 24000 character
  file was split into 13 parts of 204-629 prompt tokens each, described one call per part,
  summarized into one sentence that reached the `Description` column, and the second file of the
  tree was described normally afterwards. 22.3 seconds, 16 calls, run completed, nothing left
  resident.
- The first attempt at `tiered` measured the defect decision 4 answers: with
  `google/gemma-4-12b-qat` as the proposal model the run passed 600 seconds without finishing, and
  the server's listing showed the describing model and the proposal model resident at the same time.

## Decisions
1. **The chunk splitter counts characters and carries no library.** Weighed against a text-splitting
   library in the adapter package and against token-accurate splitting through the model's own
   tokenizer. The library was rejected as a dependency that does not earn its place: the split is
   ten lines of the standard library, and a *text* splitter is not a provider's concern - it would
   land in that package only because dependencies feel permitted there, which is the wrong reason.
   Token accuracy was rejected as out of scope rather than as wrong: it is genuinely the adapter's
   business, but the server offers no tokenizing endpoint (measured: `GET /tokenize` answers
   *"Unexpected endpoint or method"*), so it needs either a product SDK or a tokenizer library plus
   the model's own files, and above all a third operation on the provider contract, which is an ADR
   change. It is not needed either: by ADR 014 §5 overflow is the server's refusal, and a part that
   is still too large is routed under `chunk_too_large`. The budget is therefore honest about being
   a budget, and a chunk ends on the last paragraph or line break that fits.
2. **`init_list_param` learned to start over rather than a new component being written.** The
   `chunked` loop needs an empty accumulator per overflowing file, and the existing function writes
   `SET` without overwrite, which fails on the second file. The alternative that changed nothing -
   accumulating into a deque and draining it with a pop loop after the summary - was rejected: it
   costs a node whose only purpose is to empty a parameter, and renders the parts in a prompt as a
   Python `deque(...)` instead of the compact JSON every other collection reads as. The default is
   unchanged, so an accumulator that outlives its loop is still refused.
3. **The variants are three definitions, not three modes of one.** A mode would need a switch in
   every branch and could not be named as the evidence of a gate on its own. The cost is real and
   named: the three files share their first eleven nodes, so a fix to the walk is a fix in three
   places until something is done about it.
4. **A load became a swap in the `lmstudio` adapter, and this session's boundary was widened in the
   open to do it.** ADR 014 §2 already says the next call is "a swap, a load, or nothing at all",
   and the adapter only ever loaded: releasing happened on a node's `release` option and on
   `finalize`, so nothing gave the previous model back when the next call named a different one. A
   sequential run has no use for the model of the step before, and holding both is what makes a
   machine that fits either of them fit neither - measured, not reasoned: the first `tiered` attempt
   held two models and did not finish in ten minutes. The adapter now releases what it loaded before
   it loads another model. Only its own instances go back, so the ownership rule of decision 2 of
   `2026-08-25-implementation-1` is untouched; a release that fails does not fail the call that
   needed the memory, because the load that follows reports the memory it could not get. Recording
   this as a finding and leaving it was weighed and rejected: the gate variant this session owes
   cannot be measured honestly on a machine that holds two models at once.
5. **The proposal step of `tiered` names a placeholder model.** A node's `model` is a literal - the
   field resolves no `param.` reference - so a real identifier would pin a shipped definition to the
   model set of one machine. The placeholder follows what `example_config.json` already does, and
   the by-hand runs were made on a copy carrying a real identifier. The cost is that the variant
   does not run against any server until an operator edits one line, which the walkthrough of the
   closing session has to say.
6. **The swap is by model, not by what the model was loaded with.** The other half of the same
   question - a resident model loaded with a window this run would not have chosen - stays as
   decision 3 of `2026-08-25-implementation-2` left it: a model the server already holds is used as
   it stands, because reloading it would evict what someone else is working with.

## Open questions
- A node cannot take its model from an input, so a definition that chooses a model per node pins
  itself to one installation (decision 5). Whether `model` should resolve a reference the way the
  prompt does belongs to the ADR that owns the node contract.
- The three variants duplicate the eleven nodes of the base walk (decision 3). Whether a definition
  should be able to include another, or whether the duplication is the honest price of a template,
  is a question for the authoring scenario rather than for this ADR.
- Carried from `2026-08-25-implementation-2` and still open: the overflow class is told apart by a
  substring of an error body; a `load_config` written into a node's call options is refused by the
  chat call rather than at build time; the model listing reports the window of instances this
  adapter did not load.
- The action-registry twin of the provider-registry bug, carried from `2026-08-24-implementation-5`
  and still unowned.

## Next steps
1. The closing session of this branch: the documentation set - `README.md`,
   `docs/architecture/overview.md`, `examples/README.md`, the walkthrough of the three variants and
   the scenario registry row - then the merge and the freeze gate of ADR 014. Until it lands,
   `examples/README.md` promises a walkthrough beside every template that these three do not have.
2. Decide the action-registry twin: a `fix/` branch of its own, or a session that already touches
   the registries.

## References
- Branch: `feature/adr_014-llm-node-and-provider-adapter`.
- Definitions added: `examples/folder-inventory-to-csv-described.json`,
  `examples/folder-inventory-to-csv-tiered.json`, `examples/folder-inventory-to-csv-chunked.json`.
- Code changed: `src/workflow_engine/actions/modify_param_functions.py`,
  `src/workflow_engine/validators/output_function_validators.py`,
  `src/workflow_engine_providers/lmstudio.py` (the swap of decision 4).
- Tests: `tests/test_adr014_bus_components.py`, `tests/test_adr014_inventory_variants.py`,
  `tests/test_adr014_lmstudio_adapter.py`.
- Preceding note: `2026-08-25-implementation-2_handoff.md`.
- Related ADRs: ADR 014 (its class 4 evidence), ADR 002, ADR 011, ADR 012, ADR 016, ADR 021.
