# ADR 014: LLM node and provider adapter

## Status
Draft

## Active branch
—

## Context

The first phase 2 goal is a workflow with a clearly defined process in which language models do the
steps that cannot be done by code: classify, summarize, extract, draft. A proof of concept against
LM Studio (an OpenAI-compatible local server) already works as a registered function outside the
repository, which shows the plugin model (ADR 005) can carry a provider. It also shows what a plain
function leaves to every author and every vendor module: assembling the prompt from state, naming
the model, calling the provider, parsing the reply into typed parameters, deciding which failures
are retryable, and keeping prompt and reply for audit. Done per vendor, that is duplicated; done per
workflow, it takes two or three nodes for one model call.

What the core has today that a model call needs: `FunctionAction` with engine-resolved
`param.`/`output.`/`artifact.` arguments (top level only — ADR 012 deferred question §1), typed
`param_writes` through codecs (ADR 006), artifacts for durable by-products (ADR 011), the
`max_attempts`/self-loop retry allowance (ADR 002), the engine configuration file (ADR 008), and the
help contract that exposes registered components (ADR 009). What it lacks: a place for provider
configuration and secrets, a notion of a provider at all, structured parsing of a text reply into
declared parameters, and an error classification that a retry policy could act on.

Constraints:
- Dependencies stay minimal; the standard library is preferred (general rule 9). Vendor SDKs are not
  part of the core.
- Phase 2 is additive (session `2026-08-19-architecture-1`).
- ADR 013 defines the declaration and binding of a typed answer; this ADR reuses it rather than
  defining a second one.
- Guards stay deterministic boolean predicates over values (ADR 002); a model is never a guard.

## Decision

Draft. The direction below is proposed; the open points are listed at the end of this section.

### 1. A provider-neutral LLM action in the core

A core action (working name `llm`) whose node configuration declares:

- `provider`: the name of a registered provider adapter;
- `model`: a model identifier passed to the adapter, optionally defaulted by the provider
  configuration;
- `prompt`: the prompt text, or `prompt_ref`: an `artifact.` reference or path to a file holding it;
  either may contain references that the engine resolves;
- `answer`: the typed answer declaration of ADR 013 — which parameters the reply must yield and
  how they are typed — plus a `format` (`text` | `json`) that tells the action how to read the reply;
- optional provider call options (temperature, max tokens, …) passed through opaquely.

The action resolves the prompt, calls the adapter, parses the reply according to `format`, decodes
the declared values through their codecs, and returns an `ActionNodeOutput` whose `param_writes`
carry them and whose `output_text` is the raw reply. A reply that cannot be parsed or misses a
required value is an error value (`llm_answer_invalid`), which guards and transitions handle like
any other node error. The action is automatic: the run does not pause.

### 2. Provider adapters as registered components

An adapter is a callable registered under a new registration kind (working name
`@register_provider`) with a fixed signature: it receives the prompt, the model, the call options
and the provider configuration, and returns the reply text or an error value with an error class.
Adapters live in external modules (ADR 005 `external_modules`); the core may ship one generic
OpenAI-compatible HTTP adapter built on `urllib` so that LM Studio and compatible servers work
without a vendor SDK — this is an open point below. Registered adapters appear in the ADR 009 help
contract as their own component type.

### 3. Provider configuration and secrets

The engine configuration file (ADR 008) gains a `providers` section: per provider name, the adapter
to use, its base URL, the default model, and the *name of the environment variable* holding the
credential — never the credential itself. A session records the provider and model each `llm` node
actually used in the journal event of the call, so a resumed or audited run knows which model
answered; whether the provider block is snapshotted into `session.json` like storage settings
(ADR 004) is an open point.

### 4. Audit as artifacts and events

Every call journals a session event (`llm_called`: node id, provider, model, status, error class,
token counts if the adapter reports them). Prompt and reply are written as artifacts under a
deterministic name (`<node_id>.prompt`, `<node_id>.reply`, attempt-numbered) when the node opts in
(`record: true`), so they can be declared deliverables or inspected after the run. Nothing new is
added to the state model.

### 5. Error classes, not retry policy

The adapter reports each failure as one of a fixed set of classes (`transient`, `rate_limited`,
`permanent`, `invalid_request`, `timeout`) which the action surfaces as the node error code. This
ADR does not decide delay or backoff: that is the retry-policy decision of the recovery note (b),
which will consume these classes. Until then the existing `max_attempts`/self-loop allowance is the
only retry.

### 6. Testing

A `fake` adapter ships with the test suite (or the core, decided below) that returns scripted
replies, so `llm` nodes are covered by deterministic tests and the example workflows never call a
network in `pytest`.

### Open points to settle before leaving Draft

1. Prompt templating: how references inside the prompt are written and resolved. Reusing the
   top-level `param.` resolution only works if the prompt is one string; a template syntax inside
   the text (e.g. `{param.name}`) is a new resolution path and decides ADR 012 deferred question §1
   for this case.
2. Whether the generic OpenAI-compatible adapter is core (one `urllib` client, no dependency, the
   route the POC took) or the first external module (the core stays free of any provider code).
3. Whether `@register_provider` is a new registry or a convention over `FUNCTION_REGISTRY` (same
   signature, recognisable by metadata). A new registry is explicit and introspectable; the
   convention needs no ADR 005 change.
4. Whether the provider block is snapshotted into the session record.
5. Whether `answer` parsing shares code with the ADR 013 answer decoding or only the declaration
   shape.
6. Whether a separate `llm` action is needed at all once ADR 013 exists, or whether an LLM provider
   can be "the far end" of an `ask` node (the engine pauses, a driver script calls the model and
   answers). That would fold this ADR into a driver convention; it is rejected in this draft because
   it makes every model call a pause-and-resume round trip and moves audit out of the engine, but
   the point must be argued, not assumed.

## Alternatives considered

### A. No core change: the model call is a registered function
The shape of the POC. Zero core cost, maximal freedom. Rejected as the only mechanism: every vendor
module re-implements prompt assembly, parsing, typing and audit; a single model step costs several
nodes; provider configuration and secrets have no sanctioned place; the help contract cannot tell an
author which models exist.

### B. Vendor clients inside the core
`openai`, `anthropic` and similar SDKs as dependencies, one action per vendor. Fastest to a rich
feature set, but it puts dependency churn, credentials handling and provider semantics into the
engine, contradicts rule 9, and ties the release cadence of the core to vendors. Rejected.

### C. A generic "structured-output action" with no notion of a model
The core learns only "call a registered function and bind its reply to declared typed parameters";
models are functions by convention. Smaller than the decision above and provider-blind by
construction. Not chosen as the framing because provider configuration, secrets, error classes and
call audit are model-specific needs that would stay unowned; but its spirit is kept: the core action
is provider-neutral and the binding declaration is shared with ADR 013.

### D. A model as guard or validator
An LLM-as-judge predicate. Technically representable as a function guard; rejected because guards
are deterministic, recorded in state and replayed on resume, and a non-deterministic predicate there
breaks resume equivalence (ADR 006). A judgement is a node whose typed answer a deterministic guard
then reads.

## Consequences

- Enables: one node per model step, vendor-neutral workflows, typed model output on the bus, audit
  of every call, a place for credentials, and error classes a later retry policy can use.
- Costs: a new core action, a registration kind and its help-contract adapter, a `providers`
  config section, two or three session event codes, a fake adapter for tests, and the prompt
  resolution decision.
- Closes off: vendor SDKs in the core; models as guards.
- Leaves open: retry/backoff (recovery note (b)); token or cost budgets next to the node cap
  (ADR 010) — not in scope until a run shows the need.

## Related ADRs

- Depends on: ADR 005 (registration and external modules), ADR 006 (typed writes), ADR 008
  (configuration file), ADR 011 (artifacts), ADR 013 (answer declaration).
- Touches: ADR 002 (guards stay deterministic), ADR 004 (session record, if snapshotted), ADR 009
  (help contract gains a component type), ADR 012 (deferred question §1).

## Implementation notes

The existing out-of-repository LM Studio POC is the reference for the adapter signature. A POC
under this ADR, if needed, answers open points 1 and 6: an example workflow with two `llm` nodes
(extract → summarize) running against the fake adapter in tests and against LM Studio by hand, with
the prompts and replies recorded as artifacts.

## Change log

- 2026-08-19: opened as Draft in session `2026-08-19-architecture-1`.
