# Session 2026-08-25-implementation-8

## Type
implementation

## Goal
Execute roadmap step 13: run the shipped `reorganize-folder` plan variant against live local
models through the `lmstudio` adapter as the rehearsal of the drift-B stack — the adapter, the
JSON binding, the answer-keys guard, the paragraph prompt — recording the findings and applying
any prompt fixes, adding no feature.

## Completion criteria
- The shipped definition runs against more than one live local model of different classes
  (a very small model, a fast mid-size model, a reasoning model) and against more than one
  configured context length, so the differences are observed rather than assumed.
- The model swap is exercised: consecutive runs under one `lmstudio` provider show the previous
  model released when the next is loaded.
- The findings are recorded in this note as facts per stack layer: adapter behavior including
  load and release, the JSON binding against replies that wrap or annotate the object, the real
  re-ask rate of `is_answer_keys_valid`, the behavior of the ~1750-character inline decision
  prompt, and per-model differences that matter for choosing a model in a scenario.
- Prompt fixes, if any run shows they are needed, are applied to the shipped example and covered
  by `uv run pytest` and `uv run ruff check .`; if none are needed, that is stated.
- The engine configuration with the provider block and the scanned tree stay outside the
  repository.

## Scope boundaries
- No feature work: no new components, no engine changes, no new example variants. A problem whose
  fix is not a prompt edit is recorded as a finding, not fixed.
- The `load-test-triage` scenario, the data generators and the drift-B protocol stay untouched
  (roadmap steps 14–15).
- Model quality is observed, not benchmarked: no timing harness, no scoring beyond what the runs
  themselves show.

## Status
`completed`

## Result
The shipped definition ran against four local models (`liquid/lfm2.5-1.2b`,
`qwen/qwen3-4b-2507`, `mistralai/ministral-3-3b`, `qwen/qwen3-4b-thinking-2507`) at 8k, 16k and
32k configured context lengths, on a fourteen-file tree with two planted duplicate pairs. One
prompt fix was applied. Two throwaway probe definitions (a text-format classification variant and
a two-`llm`-node pair) were built outside the repository as measurement instruments and are
recorded here, not shipped. `uv run pytest` (808 passed) and `uv run ruff check .` ran clean
after the prompt fix.

## Findings, by stack layer

### Adapter and residency
- Load-as-swap holds within one provider block: with a node-level `model` override, polling the
  server during the run showed the first model released at the moment the second loaded, and
  everything released at the end. Release also happens after a failed run.
- A killed operator process leaves the model resident and the session lock in place — the
  documented contract (`finalize` never ran), now observed live.
- **Gap, confirmed by polling:** with two provider blocks on one server the swap does not cross
  them — both models sat loaded simultaneously and the first was released only at run end,
  against the adapter's own "a run uses one model at a time" rationale. A second block naming the
  same model with a different `load_config` silently uses the resident instance as it stands, so
  the settings are not applied. Fix designed and split into its own session (see Decisions).

### JSON binding (ADR 014)
- The wrapper tolerance earns its keep: fenced and prose-wrapped objects bound cleanly, and a
  reasoning model's reply arrived already stripped of its thinking, so the first-object scan was
  not even needed for it.
- What the binding refuses is exactly what it promises to refuse: the syntax of the object
  itself. `lfm2.5-1.2b` emits a deterministically malformed object (a missing colon),
  byte-identical across four attempts and across 8k/32k context — so a retry of
  `llm_answer_invalid` with an unchanged prompt against a deterministic server is three wasted
  calls ending in `max_attempts_exceeded`. `ministral-3-3b` fails the large decision answer
  structurally every time, differently each time (unquoted prose; after the prompt fix, the
  prose quoted but nested inside a spurious object; deleted files put into `moves` with `//`
  annotations; once, a path with a mangled segment) — a capability boundary of the model class,
  not a prompt defect. The mangled path is direct evidence for the applying half's deterministic
  validation of every move against the file system.

### Answer-keys guard (G4)
- Real re-ask rate on the model that binds cleanly: zero across two full runs —
  `counts_by_category` keys were always drawn from the configured list. The live rehearsal never
  exercised the guard's refusal; its protection remains proven by the `fake`-adapter tests only.

### Timeout
- One provider-level timeout does not fit a flow whose calls differ by two orders of magnitude:
  the per-file call answered in seconds while the decision call needed ~6 minutes on the same
  4B model, so the default 300 s burned four timeout retries (20 minutes) with no progress at
  8k context. Raised to 600 s, the same run completed. A timeout retry, like an invalid-reply
  retry, repeats the same doomed call when nothing about it changed.

### Prompt
- The ~1750-character multi-paragraph inline instruction carried mechanically fine (ADR 016);
  the decision prompt reached ~9k characters total, with absolute file paths repeated per
  inventory row dominating the size — a deep scan root inflates every model call.
- The prompt fix: the decision prompt now says `plan_text` is one JSON string inside one pair of
  double quotes. It moved `ministral` from unquoted prose to quoted-but-nested (not cured), does
  not disturb the model that passes, and states the contract more precisely; kept.

### Model choice, on the rehearsal machine
- `qwen/qwen3-4b-2507` is the only model of the four that completed the example end to end:
  clean JSON throughout, a correct plan (right duplicates kept, deletions listed, keys legal),
  ~80 s for fourteen classifications, ~6 min for the decision.
- `ministral-3-3b`: classification clean and fast, decision-size answers beyond it.
- `lfm2.5-1.2b`: cannot produce valid JSON at all here — but a probe variant of the definition
  with `format: text` and a one-word answer classified 14/14 mechanically clean with zero
  re-asks. Two costs, both borne by the definition: the answer needs code-side normalization
  (the model drifts between `documents` and `Documents`, which a counts guard would read as an
  invented key), and its judgment is weaker (3–4 of 14 files misclassified). The pattern — ask a
  small model for one word, keep every structure in functions — is real and cheap, and belongs
  in the authoring guidance of phase 3.
- `qwen3-4b-thinking-2507`: unusable for small per-call judgments here — hundreds of reasoning
  tokens per one-word answer, repeated 600 s timeouts; when it did answer, the reply was clean.

## Decisions
1. **The prompt fix is the only repository change of this session** (plus this note): the
   `plan_text` member of the decision prompt is declared "one JSON string". Ministral's failure
   is recorded as a model boundary, not chased further with prompt surgery.
2. **The residency gap is fixed in its own `fix/` session, not here** — it is adapter code, not
   a prompt. The agreed design: a per-server residency registry shared by all `lmstudio`
   provider blocks of one run; a load releases every instance the run holds on that server, not
   only the requesting block's; a same-model request from another block reuses the resident
   instance when its `load_config` matches and reloads under the requesting block's settings
   when it differs; foreign instances stay untouched by default, and `release_foreign: true`
   widens to clearing the whole server before the run's first load, keeping VRAM exclusive to
   the run.
3. **The text-format classification pattern is recorded, not shipped**: the probe stays outside
   the repository; where the guidance lands (an architecture note now or the phase 3 authoring
   documentation) is left open.

## Open questions
- Should a node be able to scope the call timeout, when one provider serves calls that differ by
  two orders of magnitude? Today the timeout is a provider option only.
- Should the retry route distinguish a deterministic `llm_answer_invalid` from the transient
  classes? Re-asking an unchanged prompt on a temperature-0 server cannot succeed, and the
  bounded retry spends its budget knowing nothing changed.
- Where the "one-word answer plus functions" small-model pattern is documented (an architecture
  note now, or the phase 3 authoring guidance).

## Next steps
1. The `fix/` session implementing decision 2 (the residency registry and the widened
   `release_foreign`).
2. Roadmap step 14: the data-generation discussion, then the generators and the drift-B
   protocol.

## References
- Branch: `fix/reorganize-folder-live-rehearsal`
- ADRs: ADR 014 (`llm` node, provider adapters), ADR 002 (`is_answer_keys_valid`), ADR 016
  (inline prompt interpolation), ADR 021 (call audit, read throughout as the findings channel)
- Documents changed: `examples/reorganize-folder.json` (the decision prompt), this note
