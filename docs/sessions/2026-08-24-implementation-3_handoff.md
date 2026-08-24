# Session note: 2026-08-24 implementation 3

## Type
`implementation`

## Goal
Build the provider seat of ADR 014 — the fifth registration kind, the adapter contract with its
error classes, the `fake` adapter, the `providers` configuration section and the help surface —
so that the `llm` action of the next session has a provider to call.

This is session 1 of the four sized in `2026-08-24-investigation-1`, all on the branch
`feature/adr_014-llm-node-and-provider-adapter`, merged once.

## Completion criteria
- A fifth registry (`@register_provider`) holds provider adapters by name, refusing a duplicate
  registration and an unknown lookup with the project's own configuration error.
- The adapter contract is fixed in one base class: construction from the resolved provider
  configuration, one call operation taking the prompt, the model and opaque call options, a reply
  that is either text or an error value carrying one of the six ADR 014 §5 classes, and a
  `finalize(reason)` that defaults to doing nothing.
- Provider instances are seated per configured provider name and reused inside one process, so an
  adapter may hold state — which model a local server currently has resident — and a registered
  function of an adapter package reaches the same instance the action uses.
- `start_workflow` finalizes the seated providers on every exit path, with the reason derived from
  the outcome of the run (`completed`, `failed`, `paused`, `aborted`).
- The `fake` adapter ships in the core, registered through the core module manifest: scripted
  replies, no network.
- The engine configuration carries a `providers` section — per name the adapter, the base URL, the
  default model and the *name* of the credential environment variable — and it does not enter
  `session.json`.
- Operator help gains the provider component type: its own collection key, its type description,
  a component payload that lists the call options an adapter understands, and the core/external
  split in the component report.
- ADR 014 records both departures from its text in its change log: the adapter as a registered
  class with a seated instance and a `finalize`, and the unload-after-use flag as an opaque call
  option rather than a field of the core.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No `llm` action: the node, the reply parsing, the decode path shared with the ADR 013 answer
  binding and the call audit are session 2, which also amends ADR 014 §4 to land the audit in the
  ADR 021 record channel.
- No real provider: the adapter package speaking to a local model server is session 3.
- No class 4 evidence and no `README.md` / `docs/architecture/overview.md` edits: they land in
  session 4 with the whole delivered surface, in this same branch.
- The core learns neither `load` nor `unload`: model residency stays inside an adapter.

## Status
`completed`

## Result
All completion criteria are met.

- `providers/base_provider.py`: the contract in one module - the six error classes of §5, the five
  finalization reasons, `ProviderCall` with its opaque options, `ProviderReply` as either text or a
  classified failure, `ProviderUsage`, `ProviderSettings` with the credential held by variable name,
  and `BaseProvider` with `complete` and a `finalize` that defaults to doing nothing.
- `registry/provider_registry.py`: `@register_provider` with the operator metadata a provider
  needs - the call options it acts on and the configuration keys it reads - refusing a duplicate
  name, a class outside the contract and a nameless registration.
- `providers/provider_seat.py`: the installed configuration and one instance per configured provider
  name, seated on first use, reinstalled without losing what an unchanged adapter remembers,
  finalized and unseated together.
- `providers/fake_provider.py`: the `fake` adapter in the core module manifest, answering from a
  scripted sequence, from a call option, or with the prompt itself.
- The engine finalizes the seated adapters on every exit path of `start_workflow`, with the outcome
  read from the last session event before the completion export records events of its own.
- The engine configuration carries `providers`; a session record still carries only what a resume
  needs, and the credential variable name never reaches it.
- Operator help gained the provider component type end to end: the collection key, the type
  description, the component payload with the call options as its parameters and the configuration
  keys beside them, the core/external split of the component report, and the `--component-type`
  choices of the two help commands, which read the same map.
- ADR 014 carries all three departures in its body and its change log.
- 51 tests added in four files; `uv run pytest` 566 passed, `uv run ruff check .` clean,
  `uv run ruff format .` applied.

## Decisions
1. **An adapter is a class with a seated instance, not a plain callable.** ADR 014 §2 wrote it as a
   callable; a local model server makes that wrong. The adapter has to remember which model is
   resident to decide whether the next call is a swap, a load or nothing, and it has to be told when
   to release it. Recorded as an amendment in the ADR change log.
2. **The seat is module state, like the registries.** The alternative was an instance owned by the
   `WorkflowEngine` object. Rejected: the way a node reaches provider-specific work - releasing a
   model - is a registered function of the adapter package, and a function receives only the state
   view and the previous output, so it could never reach an engine-owned seat. The cost is one seat
   per process, which for one model server is the truth, and a test fixture that resets it.
3. **Model residency stays entirely inside the adapter.** Switching happens inside the call, where
   the state already is; releasing right after a call travels as one of the opaque call options that
   §1 already sanctions. The rejected alternative was a core-declared node field with
   `load`/`release` on the base class: it would teach the core a concept that is a no-op for every
   cloud provider and would widen a contract §2 deliberately narrowed to the signature and the
   error classes.
4. **`finalize` carries the reason.** A bare `close()` would leave the adapter unable to tell a
   pause from an end, so it would either thrash the model on every question or hold it after the
   run. Four
   reasons are run outcomes; `reconfigured` says the seat itself is being rebuilt, so an adapter is
   never told a run ended when none did.
5. **A failure to release is reported, not raised.** It lands on the response under a `provider:`
   key, which the command result carries and the exit code ignores: the run already reached its
   outcome, and a model left resident is an operator's problem rather than a failed workflow.
6. **A configured provider resolves lazily.** Bootstrap installs the section but does not check
   that every adapter it names is registered, so an installation missing the plugin of a provider it
   never calls still runs. The error arrives at the first call of that provider, as a configuration
   error.
7. **An unknown key inside a provider block fails the load.** Adapter-specific settings have their
   own place under `options`, so a sixth key is a typo, and a typo found at the first model call is
   found too late.

## Open questions
- Whether the `llm` node names its provider by the configured name only, or may also select the
  adapter directly. Session 2 decides it with the action's configuration.
- What the call audit records and where: ADR 014 §4 still says a journal event, and session 2 amends
  it to the ADR 021 record channel as the `llm` details.

## Next steps
1. Session 2 on this branch: the `llm` action - prompt resolution under ADR 016, the call, reply
   parsing by `format`, the decode path shared with the ADR 013 answer binding, the error classes as
   node error codes - and its audit, amending ADR 014 §4 to land it in the node-record channel.
2. Session 3: the adapter package in this repository, with its own tests, its example
   `external_modules` configuration and a by-hand run against a local model server.
3. Session 4: the `described`, `tiered` and `chunked` variants of `folder-inventory-to-csv` as the
   class 4 evidence, the documentation set (`README.md`, `docs/architecture/overview.md`, the
   walkthrough, the scenario registry), then the merge and the freeze gate.

## References
- Branch: `feature/adr_014-llm-node-and-provider-adapter`.
- Code: `providers/base_provider.py`, `providers/provider_seat.py`, `providers/fake_provider.py`,
  `registry/provider_registry.py`, `help_contract/adapters/providers.py` (all new);
  `bootstrap/config_loader.py`, `bootstrap/component_loader.py`, `bootstrap/plugin_manifest.py`,
  `bootstrap/bootstrap.py`, `help_contract/models.py`, `help_contract/builder.py`, `engine.py`.
- Tests: `tests/test_adr014_provider_contract.py`, `tests/test_adr014_provider_seat.py`,
  `tests/test_adr014_provider_help.py`, `tests/test_adr014_provider_finalization.py` (all new);
  the component type sets of `tests/test_help_contract.py` and `tests/test_cli_contract.py`, and a
  seat fixture in `tests/conftest.py`.
- Documents changed: `docs/adr/adr-014-llm-node-and-provider-adapter.md`, this note.
- Related ADRs: ADR 014 (implemented here), ADR 005, ADR 008, ADR 009, ADR 013, ADR 021.
- Preceding note: `2026-08-24-implementation-2_handoff.md`.
