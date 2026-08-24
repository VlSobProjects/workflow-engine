# Session note: 2026-08-24 implementation 5

## Type
`implementation`

## Goal
Deliver the provider-adapter package ADR 014 §2 keeps in this repository — one OpenAI-compatible
adapter over the standard library, registered as an external module rather than as a core
component — prove it against a local model server by hand, and settle from that evidence how much
of a wrapped reply `format: json` tolerates.

This is session 3 of the four sized in `2026-08-24-investigation-1`, all on the branch
`feature/adr_014-llm-node-and-provider-adapter`, merged once.

## Completion criteria
- A second top-level package under `src/`, `workflow_engine_providers`, outside the core module
  manifest and reached only through an `external_modules` entry, so the plugin model of ADR 005 is
  exercised by a real consumer for the first time.
- One adapter, `openai_compatible`, speaking `POST <base_url>/chat/completions` over the standard
  library: no new dependency, the prompt as a single user message, the credential read at call time
  from the environment variable the provider block names, and call options passed into the request
  body unread except for the ones the adapter documents as its own.
- Every failure the transport can produce is returned as one of the six classes of ADR 014 §5, never
  raised, so the node routes on it: the classification is stated in the code and covered by tests.
- The reply is read back into the contract of §2: the text, the model the server reports, and the
  token counts it reports as `ProviderUsage`.
- The adapter declares its operator metadata like every other registered component, so
  `help-component --component-type providers` describes it and reports it as external.
- Tests that reach no network beyond loopback: a scripted HTTP server on an ephemeral port covers
  the successful call, the read-back, the option and credential handling, and each error class.
- An example configuration shipped beside the package showing the `external_modules` entry and the
  matching `providers` block, with the credential named and never carried.
- A by-hand run of an `llm` node against a local model server, reported with what actually ran.
- The fenced-reply question of `2026-08-24-implementation-4` is decided against that evidence, and
  the decision is recorded in this note and in ADR 014.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No second adapter: an adapter that manages model residency is not written here, so nothing in this
  session exercises `finalize` against a real server.
- No `README.md`, no `docs/architecture/overview.md`, no walkthrough and no scenario registry edits:
  the whole delivered surface is documented in session 4, in this same branch.
- No class 4 gate variants: `described`, `tiered` and `chunked` are session 4.
- No change to the `llm` action beyond what the reply-reading decision requires.
- No productization of the package: no second distribution, no separate version, no release story.

## Status
`completed`

## Result
All completion criteria are met.

- `src/workflow_engine_providers/`: the add-on package, a second top-level package beside the
  engine, outside the core module manifest. `openai_compatible.py` holds its one adapter,
  `example_config.json` the configuration that reaches it. The wheel ships it; nothing imports it
  until an installation names it in `external_modules`.
- The adapter speaks `POST <base_url>/chat/completions` on the standard library alone, so the
  reference plugin adds no dependency. The prompt is one user message, an optional `system` message
  precedes it, the credential is read from the named environment variable at the moment of the call
  and sent as a bearer token, and every option except `timeout` and `system` reaches the server
  unread. The reply is read back as the text, the model the server reports and the token counts it
  reports.
- Every transport failure is one of the six classes and none of them is an exception: 429 rate
  limited, 408 and a read that does not complete a timeout, 413 and a 4xx body naming the context an
  overflow, 401/403 permanent, another 4xx an invalid request, a 5xx and an unreachable server
  transient, and a body that is not a chat completion permanent.
- `format: json` now reads the reply as it stands and, where that is not JSON, takes the first JSON
  object the reply carries, ignoring `//` and `/* */` notes between its members. The by-hand runs are
  why, and they also fixed where the tolerance stops: see decision 1.
- A bug that only a real plugin could show: `get_registered_providers_info` returned the registry
  itself, so the component loader compared the set of core adapters against a set that had meanwhile
  grown, and every adapter a plugin registers was reported as if the core shipped it. It now returns
  a snapshot, and `help-component` reports the adapter as `Source: external`.
- The `options` help of the `llm` node pointed at `show-component --component-type provider`, which
  is neither a command that exists nor a component type that exists. It now names the one that does.
- 55 tests added: 40 in `tests/test_adr014_adapter_package.py`, against a scripted HTTP server on a
  loopback port, and 15 in `tests/test_adr014_llm_action.py` for the wrapped reply, written against
  the shapes the models actually produced. `uv run pytest` 678 passed, `uv run ruff check .` clean,
  `uv run ruff format .` applied.

What ran by hand, and against what. Two local model servers were used, both reached over the same
OpenAI-compatible protocol and both through the installed CLI, which is the point: the adapter is
written against a protocol, not against a product, and running it on two of them is what shows that.
Nine replies were sampled across six models and two prompt styles. Runs of the `llm` node itself: a
`format: text` node; a `format: json` node that failed as `llm_answer_invalid` because the model
declined the task and said so inside a fenced object, which is the correct verdict; and `format:
json` answered by three models in turn, each binding `category` and `pages` — the last as a typed
`int` — with the record of the visit carrying the model and the token counts. Two failures were
provoked against a real server: a model the server does not hold, classified `invalid_request`, and
a hundredth-of-a-second budget, classified `timeout`. Every model loaded by hand was unloaded again.

## Decisions
1. **`format: json` ignores what surrounds or annotates the object, and repairs nothing inside it.**
   The open question of `2026-08-24-implementation-4`, decided on measurement rather than on paper.
   Of nine replies sampled from two servers, six arrived inside a fenced code block or surrounded by
   prose, two of those despite a prompt that forbade the fence, and one annotated a member with a
   `//` note that no strict parser accepts. A strict reading refuses exactly the models the decision
   exists to call. Alternatives weighed: stripping a fenced block teaches the action about markdown
   and still misses the object that sits in prose without a fence, which the sample also contains;
   keeping the strict reading behind an opt-in flag leaves the default the one that fails two times
   in three and makes every author learn the flag; a full repair pass — trailing commas, quote
   styles, Python literals — turns the action into a JSON repair library that guesses what the model
   meant. The line drawn instead is between annotation and syntax: a fence, a sentence and a comment
   surround or annotate the object and are ignored; a trailing comma, a single-quoted key and a
   Python literal are the object itself and stay refused. The reply is read exactly as it came before
   any note is removed, and the comment scan tracks strings, so the `//` of a URL inside a value is
   never mistaken for a comment. The residual cost: a reply whose prose carries a JSON object before
   the real answer binds the wrong one. Nothing is hidden either way — the raw reply stays the output
   text of the node and the reply artifact of the call.
2. **One protocol in this session, and residency as a second adapter rather than as options on this
   one.** The package ships `openai_compatible` and nothing else. Putting a vendor's model load and
   unload into it was weighed and rejected: that adapter is defined by speaking a protocol no vendor
   owns, so a residency option inside it would be dead on every other server an installation might
   point it at, and a node asking for a release would silently do nothing. The residency adapter is
   therefore a subclass in the same package — it inherits the chat call and adds what one product
   offers — and it is new work with its own session, not an extension of this one.
3. **The package ships inside the engine's wheel and is still a plugin.** Its externality is a fact
   of configuration, not of distribution: nothing imports it until `external_modules` names it, and
   the help contract reports it as external. A second distribution would prove the plugin model
   across a real install boundary, but it buys a workspace mechanism, a second `pyproject.toml` and
   an install step inside the test run, for a package whose productization the ADR already defers.
4. **A test that proves a plugin loads has to unload it first.** Registration is an import side
   effect, so the loader test drops the adapter from the registry and the package from the import
   cache before it runs; without that it would only observe that some earlier test imported the
   module. That test is what found the registry bug above.

## Open questions
- The twin of the registry bug: `get_registered_actions_info` returns `ACTION_DESCRIPTIONS` itself,
  the same defect in the action registry, so an action a plugin registers is reported as a core
  component. It is a one-word fix and it lies outside this task, so it was left alone rather than
  folded in. The function, validator and codec registries build a fresh dictionary and are unaffected.
- A reasoning model was measured and is not a problem on the servers tested: the thinking arrives in
  a field of its own beside the content, and the adapter reads the content, so it never reaches the
  extraction path. The untested case is a server that inlines the thinking into the content instead;
  there a brace inside the reasoning could be bound in place of the answer. No sampled reply did it.
- Whether the thinking a server reports separately is worth keeping for the audit. The adapter drops
  it today, because the contract of §2 is text in and text out, and widening it is a decision.
- Whether the seat and `finalize` survive contact with a server that holds a model resident. Nothing
  in this repository exercises them beyond the `fake` adapter, and the decision that an adapter is a
  class rests on exactly that case. This is what the next session settles.
- Whether the first-object scan needs a bound. It reads the whole reply, so a very long reply full of
  braces costs more than parsing the reply once. No sampled reply came near it, so no bound was
  invented for a cost nobody has measured.

## Next steps
1. The residency adapter, its own session on this branch: a subclass of `openai_compatible` for a
   local server that loads and unloads models, with the release travelling as a call option and the
   unload decided in `finalize`. It is the first thing to exercise the provider seat and `finalize`
   against a real server, which is the case ADR 014 §2 made an adapter a class for.
2. Session 4, on this branch: the `described`, `tiered` and `chunked` variants of
   `folder-inventory-to-csv` as the class 4 evidence, then the documentation set — `README.md`,
   `docs/architecture/overview.md`, the walkthrough and the scenario registry, including how an
   operator reaches this package — then the merge and the freeze gate.
3. Decide the action-registry twin above: a `fix/` branch of its own, or folded into a session that
   already touches the registries.

## References
- Branch: `feature/adr_014-llm-node-and-provider-adapter`.
- Code added: `src/workflow_engine_providers/` — `__init__.py`, `openai_compatible.py`,
  `example_config.json`.
- Code changed: `src/workflow_engine/registry/provider_registry.py`,
  `src/workflow_engine/actions/action_llm.py`, `pyproject.toml`.
- Tests: `tests/test_adr014_adapter_package.py` (new), `tests/test_adr014_llm_action.py`.
- Documents changed: `docs/adr/adr-014-llm-node-and-provider-adapter.md`, this note.
- Preceding note: `2026-08-24-implementation-4_handoff.md`.
- Related ADRs: ADR 014 (implemented here), ADR 005, ADR 008, ADR 009, ADR 013, ADR 021.
