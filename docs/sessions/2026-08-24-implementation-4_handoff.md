# Session note: 2026-08-24 implementation 4

## Type
`implementation`

## Goal
Build the `llm` action of ADR 014 — the node that resolves its prompt, calls the seated provider,
parses the reply by its declared `format`, decodes the declared values through the codecs and
surfaces every failure as a routable node error code — together with its call audit, which lands in
the node-record channel of ADR 021 rather than in the session journal.

This is session 2 of the four sized in `2026-08-24-investigation-1`, all on the branch
`feature/adr_014-llm-node-and-provider-adapter`, merged once.

## Completion criteria
- A core action `llm`, registered through the core module manifest, whose node declares `provider`,
  an optional `model`, a `prompt` that is template text under ADR 016, the ADR 013 `answer`
  declaration, a `format` (`text` | `json`), opaque call `options` and an optional `record` flag.
- The prompt is validated as template text when the node is built and resolved when the node runs,
  so a malformed template is a configuration error and an unresolved reference fails the run.
- `format: text` binds the whole reply to at most one declared name; a second declaration under
  `text` is a node configuration error. `format: json` reads a JSON object whose keys are the
  declared names.
- The decoding of declared values — the declared shape plus raw values in, typed writes or a refusal
  out — is one code path shared with the ADR 013 answer binding, so the two declarations cannot
  drift.
- The six error classes of ADR 014 §5 are the node's error codes as they are, an unreadable reply
  is `llm_answer_invalid`, and an adapter that raises instead of returning a classified failure is
  `provider_failed`, kept apart from the six so a broken plugin never reads as a rate limit.
- An unconfigured provider, an adapter no module registered and a call with no model resolved are
  configuration errors that are not routable, raised at the call as session 1 decided.
- The call audit is the `details` member of the ADR 021 record of the visit: provider, model,
  status, error class and the token counts the adapter reported. `ActionNodeOutput` carries the
  details the engine copies into the record.
- With `record: true` the prompt and the reply are written as artifacts under `<node_id>.prompt` and
  `<node_id>.reply`, numbered by the visit and attempt ordinals of ADR 017, so an artifact and the
  record of the same visit carry the same two numbers.
- ADR 014 records in its body and its change log that §4 audit is a node record rather than a
  journal event, and that `provider_failed` is the action's own code beside the six classes.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No real provider: the adapter package speaking to a local model server is session 3, and with it
  the decision whether `format: json` tolerates a fenced code block around the object.
- No class 4 evidence and no `README.md` / `docs/architecture/overview.md` / walkthrough edits: they
  land in session 4 with the whole delivered surface, in this same branch.
- No `pre_functions` / `post_functions` and no `prompt_ref`: both sit in Leaves open with their
  triggers.
- No retry policy: the existing `max_attempts` self-loop allowance stays the only retry.

## Status
`completed`

## Result
All completion criteria are met.

- `actions/action_llm.py`: the `llm` action in the core module manifest - the node contract, the
  prompt resolved under ADR 016, the call through the seated adapter, the reply read by `format`,
  the six classes as node error codes, and the audit of every call.
- `declared_values.py`: the shared binder. The declared shape plus raw values in, typed `SET` writes
  and their codec names out, `subject` naming the transport in every message. `bind_answer` was
  rewired onto it and lost its own copy of the undeclared, missing-required and decode steps.
- `ActionNodeOutput` gained `details`, the open member the engine copies into the node record of the
  visit; `_record_visit` carries it. Nothing else reads it.
- `StateModel.visit_ordinals` replaced the engine's private helper and is exposed on the read-only
  view, so the action numbers its audit artifacts by the ordinals of ADR 017 §4. The
  `interactive_answered` event now computes them there too, instead of repeating the arithmetic.
- ADR 014 carries the amendments in §4, §5, §1, §3, Consequences and the change log.
- 57 tests added in two files - the node contract and the reply reading in one, a model step inside
  a real run in the other; `uv run pytest` 623 passed, `uv run ruff check .` clean,
  `uv run ruff format .` applied.

## Decisions
1. **The audit travels on the action's output.** `ActionNodeOutput` gains an open `details` member
   which the engine copies into the record of the visit. The alternatives were an engine that asks
   the action for its details after the fact — which would make the action hold the last call
   between visits — and an engine that knows the `llm` action by its type, which puts one action
   into the step loop. The cost is that a function returning a fresh output drops the details; the
   `llm` node runs no function chain, so nothing loses them today.
2. **`format` decides how many names the reply may carry.** `text` is one value and refuses a second
   declaration when the node is built; `json` is an object keyed by the declared names. A reply that
   does not fit is `llm_answer_invalid`, routable, with the raw reply kept as the output text so the
   evidence of what the model said is not thrown away.
3. **The visit ordinals move into the state model.** `_visit_ordinals` was a private helper of the
   engine; it becomes `StateModel.visit_ordinals` and is exposed on the read-only view, so the
   action numbers its audit artifacts by the same two numbers the record carries. The alternative —
   picking the next free artifact name — would have numbered calls rather than visits.
4. **An adapter that raises fails the node under `provider_failed`.** The contract says a failure is
   a value; an exception means the adapter broke it. Letting it end the run would lose a workflow to
   a plugin's bug, and folding it into `transient` would let a bug be retried as a hiccup.
5. **An audit that cannot be written fails the node under `llm_record_failed`.** Not planned at the
   start of the session; it is the third code the action owns. A node that asked for `record: true`
   asked for the audit, so silently dropping it would report a call as fully accounted for when it
   is not, and the reply survives as the output text either way. A failed call is the exception: it
   already carries its classification, so a prompt file that cannot be written is left out rather
   than turned into a second, different failure.

## Open questions
- Whether `format: json` stays strict. A local model often wraps its object in a fenced code block,
  and the cleaning chain that would have stripped it was cut by G1. Extraction is the action's own
  concern, so the tolerance would be legal inside `format: json`; the decision waits for session 3,
  where the first by-hand run against a real model says whether it is needed.
- Whether an audit artifact belongs under `record: true` at all once the record stream carries the
  account of the call. The artifacts hold what the record deliberately does not - the prompt and the
  reply themselves - so they stay, but the gate variants of session 4 are what will show whether a
  workflow ever declares one a deliverable.

## Next steps
1. Session 3: the adapter package in this repository, with its own tests, its example
   `external_modules` configuration and a by-hand run against a local model server; it also settles
   the fenced-reply question above.
2. Session 4: the `described`, `tiered` and `chunked` variants of `folder-inventory-to-csv` as the
   class 4 evidence, the documentation set (`README.md`, `docs/architecture/overview.md`, the
   walkthrough, the scenario registry), then the merge and the freeze gate.

## References
- Branch: `feature/adr_014-llm-node-and-provider-adapter`.
- Code: `actions/action_llm.py`, `declared_values.py` (both new); `answers.py`, `output.py`,
  `models/state.py`, `engine.py`, `bootstrap/plugin_manifest.py`.
- Tests: `tests/test_adr014_llm_action.py`, `tests/test_adr014_llm_e2e.py` (both new).
- Documents changed: `docs/adr/adr-014-llm-node-and-provider-adapter.md`, this note.
- Preceding note: `2026-08-24-implementation-3_handoff.md`.
- Related ADRs: ADR 014 (implemented here), ADR 013, ADR 016, ADR 017, ADR 021, ADR 006, ADR 011.
