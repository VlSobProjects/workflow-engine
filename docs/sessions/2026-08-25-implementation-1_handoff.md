# Session note: 2026-08-25 implementation 1

## Type
`implementation`

## Goal
Give the provider package a second adapter for a local model server that manages model residency,
as a subclass of `openai_compatible` that inherits the chat call and adds only what one product
offers — so that the provider seat and `finalize(reason)`, the two mechanisms ADR 014 §2 made an
adapter a class for, are exercised against a real server for the first time.

This session is not one of the four sized in `2026-08-24-investigation-1`. It was opened during
session `2026-08-24-implementation-5`, when the residency API turned out to be reachable and the
question of where it belongs was decided; it runs on the same branch,
`feature/adr_014-llm-node-and-provider-adapter`, and merges with it.

## Completion criteria
- A second adapter registered in `src/workflow_engine_providers/`, subclassing the OpenAI-compatible
  one: the chat call, the error classes and the reply reading are inherited unchanged, and only
  residency is added. Nothing product-specific is added to `openai_compatible` itself.
- The adapter finds the server's native API from the configured `base_url`, with an explicit
  override available in the provider block's `options` for a server that publishes it elsewhere.
- Residency is read from the server rather than assumed: before a call the adapter asks which
  instances are loaded, and loads the model when none is.
- The adapter releases only the instances it loaded itself. A model the operator had loaded before
  the run is never unloaded by a workflow.
- The residency memory is a cache of a fact outside the process, as ADR 014 §2 requires: the adapter
  works with it empty, re-checks the server before releasing, and treats a disagreement as the
  server being right.
- `release` as a call option: a node that asks for it has the instance that served the call
  unloaded once the reply is in hand. A failed release never turns an answered call into a failed
  node.
- `finalize(reason)` decides the release by the outcome, with the reason it is told: released on a
  run that ended, kept on a pause where the next call is expected shortly. The policy is the
  adapter's own and is stated in its help entry.
- A failure of the residency API is classified like any other provider failure: a model the server
  does not have is not a transient hiccup, and a server that cannot be reached is.
- Tests against a scripted loopback server extended to serve the residency endpoints, covering the
  load decision, the ownership rule, the call option, each `finalize` reason and the failures.
- A by-hand run against the real server: a model loaded by the adapter, used, and released, verified
  by asking the server what it holds before and after.
- ADR 014 records in its body and change log that the residency adapter exists, what it is allowed
  to release and why residency did not go into the protocol adapter.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No model download: what a server has installed is an operator's concern, not a workflow's, so the
  download and download-status endpoints are not wired.
- No change to the core: the provider contract, the seat, the `llm` action and the error classes
  stay as ADR 014 delivered them. If this session finds the contract wanting, that is a finding to
  record, not a change to make here.
- No second protocol beyond residency: the chat call stays the inherited OpenAI-compatible one.
- No `README.md`, no `docs/architecture/overview.md`, no walkthrough and no scenario registry edits:
  the whole delivered surface is documented in the session that closes this branch.
- No retry or backoff policy around a load, which is the recovery note's decision, not this one.

## Status
`completed`

## Result
All completion criteria are met.

- `src/workflow_engine_providers/lmstudio.py`: the `lmstudio` adapter, a subclass of
  `openai_compatible`. The chat call, the six error classes and the reply reading are inherited
  untouched; the subclass adds the server's own model API beside them and nothing else. The parent
  gained exactly one thing for it — the options an adapter consumes rather than forwards are now a
  class attribute a subclass extends, so an instruction meant for the adapter never reaches the
  server as a field of the request.
- The native API root is derived from the configured `base_url` and can also be declared outright in
  the provider block, because a derivation is a guess about someone else's URL layout and a guess
  must not be the only way through.
- Before a call the adapter asks the server which instances it holds and loads the model when none
  is; a model the server already holds is left alone and deliberately not claimed. `release` as a
  call option frees the model right after the call, whether the call was answered or refused, and a
  release that fails never turns an answered call into a failed node. `finalize` releases what the
  adapter loaded on every outcome but a pause.
- Failures of the model API are classified by the same rule as the chat, and by nothing else: a
  model the server does not have is `invalid_request`, a load or a server that fails is `transient`,
  a load that answers without an instance is `permanent`. None of them is raised. Reading the wording
  of a failed load to classify it more finely was written and then removed — see decision 6.
- 31 tests in `tests/test_adr014_lmstudio_adapter.py`, against a loopback server that keeps real
  residency: a load adds an instance and an unload removes one, so a test fails when a model is left
  in memory rather than when an internal call stopped happening. The package's loader test now
  covers both adapters. `uv run pytest` 709 passed, `uv run ruff check .` clean, `uv run ruff
  format .` applied.
- `example_config.json` gains a block for the residency adapter beside the protocol one, and ADR 014
  §2 carries the split, the ownership rule and the re-checking rule, with its change log.

What ran by hand against the real server, with the server's own listing read before and after each
step: a model absent, loaded by the adapter, resident during the call, and gone after `finalize`;
the same model still resident after a pause and released once the run ended; `release` on the node
freeing it immediately; a model loaded from outside the run surviving both a node release and the
end of the run; and a model the server does not have coming back as `invalid_request`. A full run
through the installed CLI completed with the model released by the engine's own finalization.

Four facts about a real server were measured rather than assumed. A model far larger than the
graphics memory loads anyway: the server spills it into system memory instead of refusing, so scarce
video memory makes a call slow rather than failing it, and a node meets that as a timeout if it meets
it at all. A machine too small for a model refuses in two different ways — predicted before any
allocation, in a sentence naming the memory it would have needed and costing a tenth of a second; and
discovered while allocating, after tens of seconds, saying nothing at all beyond the fact that the
load failed. The second was reached twice, once by filling the machine with six models and once with
a single model on an otherwise idle machine, so it is the ordinary shape of an unpredicted memory
failure rather than an artefact of a crowded server. Both arrive as one status under one error type
shared with every other reason a load can fail, which is what decision 6 answers. A server under memory pressure can also fail the chat call itself with a
page of HTML rather than a JSON error; that is a 5xx like any other and the adapter classifies it
transient without reading it, and the body it quotes back is bounded. And a server may hold more than
one instance of the same model, naming the second one apart from the first, so an instance is
addressed by the name the listing gave it and never by the name of its model.

## Decisions
1. **Residency is a subclass, not an option on the protocol adapter.** Weighed against putting the
   load and unload endpoints into `openai_compatible` behind options. Rejected: that adapter is
   named after a protocol no vendor owns, so the endpoints would be absent on every other server an
   installation points it at, and a node asking for a release would silently do nothing — the same
   workflow honoured on one machine and ignored on the next. The cost of the subclass is a second
   registered name and its own tests; the benefit is that the option means what it says wherever the
   adapter is configured at all.
2. **A run releases only what it loaded.** A model the operator loaded from the application, or one
   another process loaded, is left resident even when a node asks for a release. The alternative —
   release means release — is more predictable for the author of a workflow, and it was rejected
   because the surprise lands on someone else: a run would evict the model a person is working with
   beside it. Because memory is finite and an operator may genuinely want the eviction, the
   permission exists as `release_foreign`, and it sits in the provider block rather than in the
   node: a workflow definition travels between installations and that permission must not travel
   with it.
3. **The adapter loads explicitly rather than letting the server load on demand.** The server would
   load the model on the chat call by itself, which is one request fewer. Rejected because ownership
   is what the release rules are built on: a model that appeared by itself was not loaded by this
   adapter, so decision 2 would leave `release` and `finalize` with nothing they are allowed to
   touch. The explicit load also leaves room for load-time settings a chat call cannot carry.
4. **`finalize` re-reads the server before releasing.** Found by a test rather than reasoned in
   advance: releasing straight from the memory reported a failure when another process had already
   unloaded the instance, though the goal — the model not resident — was met. The memory is a cache
   of a fact outside the process, so the listing is read first and the server wins any disagreement.
   Where the listing itself cannot be read, the releases are attempted blind and the report says so.
5. **A failure to release is raised out of `finalize` on purpose.** That is the channel the seat
   already has for it: the seat catches it, reports it on the response of the run, and leaves the
   outcome and the exit code alone. It is carried by the project's own error type rather than a bare
   exception, so nothing else in the engine has to guess what it means.
6. **A failed load keeps the class its status gives it, and the wording is not read.** This was
   decided twice. The first version read the wording: a refusal naming insufficient memory became
   `transient`, everything else under the same error type became `permanent`, on the reasoning that
   a model file the server cannot read will never become readable and retrying it burns a node's
   whole allowance. The second measurement destroyed that. Filling the machine model by model
   produced a refusal of the very same condition — memory — worded as nothing but "Failed to load
   model", after nearly a minute of actually trying: the server predicts the requirement when it
   can, and simply fails when it cannot. The rule would have called that permanent and stranded a
   run that had only to release something and try again. The same wording was then reproduced with
   one model on an idle machine, so it is the ordinary case rather than the crowded one. The permanent branch was also built on an
   invented failure: no load that can never succeed was ever observed, and its markers were guessed,
   which is the standard this session held everything else to. So the split is gone. The cost is
   named rather than hidden: a genuinely unloadable model is retried until the node's allowance runs
   out, which is the cheaper of the two mistakes on a local server, where memory is the common cause
   and a broken model file is the rare one.

## Open questions
- The six classes of ADR 014 §5 have no seat for "the machine cannot host this call right now", and
  a resource refusal is filed under `transient` for want of a better one. The promise `transient`
  makes is that the same call may succeed later, which is true here only if something outside the
  node frees memory: a bare `attempts` transition back to the node will spend the whole allowance
  re-asking a question whose answer has not changed. Whether the class set needs a seventh member,
  or whether the retry policy of the recovery note should read the classes more finely, is an ADR's
  question and not this session's.
- Whether `release_foreign` is the right shape for the resource problem it answers. It is a blunt
  permission: on, a run may evict anything; off, a run may be unable to load what it needs. The
  measurement below makes the gentler policy writable for the first time — the server refuses in a
  tenth of a second and costs nothing, so an adapter could release foreign models only after a load
  has actually been refused, rather than being permitted to in advance. Nothing was built on that,
  because which models a run may evict under pressure is a decision about someone else's work and
  wants a scenario behind it.
- Load-time settings, such as a context length, have no channel at all: the load endpoint takes the
  name of a model and rejects anything else, so what a model is loaded with is state the server
  application holds per model, set in its own interface and remembered there. An adapter cannot pass
  them, and a run cannot know them - it can only read back what the server reports about the
  instance it got. Whether that matters is a question for a scenario that needs two different
  context lengths for one model.
  **Corrected in `2026-08-25-implementation-2`:** this was assumed rather than asked, and it is
  wrong. The load endpoint does accept a load configuration, a context length among it, and the
  adapter now carries one, declared once in the provider block and forwarded unread. The claim is
  left standing rather than deleted, because the trail records what was believed and when. What
  survives of this entry is where it ended: two different context lengths for one model still want a
  scenario, and a model the server already holds is still used as it stands.
- The action-registry twin of the provider-registry bug, carried over from
  `2026-08-24-implementation-5` and still unowned.

## Next steps
1. Session 4 of the ADR 014 arc, on this branch: the `described`, `tiered` and `chunked` variants of
   `folder-inventory-to-csv` as the class 4 evidence, then the documentation set — `README.md`,
   `docs/architecture/overview.md`, the walkthrough and the scenario registry, which now have two
   adapters and a residency story to describe — then the merge and the freeze gate.
2. Decide the action-registry twin: a `fix/` branch of its own, or folded into a session that
   already touches the registries.
3. Take the resource refusal to the ADR that owns the class set, if a scenario shows a run that has
   to act on it: either a seventh class or a retry policy that reads `transient` more finely, with
   the release-under-pressure policy decided in the same place.

## References
- Branch: `feature/adr_014-llm-node-and-provider-adapter`.
- Code added: `src/workflow_engine_providers/lmstudio.py`.
- Code changed: `src/workflow_engine_providers/openai_compatible.py` (the consumed options become a
  class attribute; two helpers become shared inside the package),
  `src/workflow_engine_providers/__init__.py`, `src/workflow_engine_providers/example_config.json`.
- Tests: `tests/test_adr014_lmstudio_adapter.py` (new), `tests/test_adr014_adapter_package.py`.
- Documents changed: `docs/adr/adr-014-llm-node-and-provider-adapter.md`, this note.
- Preceding note: `2026-08-24-implementation-5_handoff.md`.
- Related ADRs: ADR 014 (implemented here), ADR 005, ADR 008, ADR 009.
