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

## Consumer

The party that acts on this decision is the model behind a registered provider adapter: the engine
builds the prompt from the declared parameters, calls the model itself inside the run and binds the
typed reply — no external answerer is involved. The freeze-gate evidence is class 4 and small on
purpose: the named variants the implementation adds to the `folder-inventory-to-csv` walkthrough —
`described` (a guard routes files of the formats a parameter lists to an `llm` node that writes a
description column), `tiered` (a second, larger model composes an optimization proposal over the
accumulated table; the model of a step is chosen per node, per-type routing is graph branching),
`chunked` (an oversized file routed on `context_overflow` through the split-and-accumulate loop) —
each covered by `fake`-adapter tests and run by hand against a local model; the walkthrough and the
scenario registry list this ADR when the feature branch merges. The phase consumer is
`load-test-triage` (`docs/architecture/scenarios/load-test-triage.md`): every judgment step there
is an `llm` node, and that scenario gates the phase, not this ADR alone — the phase exit already
gates every ADR of the phase, so a per-ADR gate stays local.

## Decision

All open points this Draft carried are settled, and session `2026-08-23-architecture-1` (G1) then
narrowed the decision to what the `load-test-triage` scenario asks of it; the cut items sit in
Leaves open with their triggers (see the change log).

### 1. A provider-neutral LLM action in the core

A core action (working name `llm`) whose node configuration declares:

- `provider`: the name of a registered provider adapter;
- `model`: a model identifier passed to the adapter, optionally defaulted by the provider
  configuration;
- `prompt`: the prompt text, declared template text under ADR 016;
- `answer`: the typed answer declaration of ADR 013 — which parameters the reply must yield and
  how they are typed — plus a `format` (`text` | `json`) that tells the action how to read the reply;
- optional provider call options (temperature, max tokens, …) passed through opaquely.

The prompt is template text under the ADR 016 contract, inherited whole rather than adapted: the
braced `${param.}`/`${output.}`/`${artifact.}` form only, `$$` for a literal `$`, a malformed
template as a node configuration error at build time, an unresolved reference as the resolution
error that fails the run, values rendered by the single rendering rule, and single-pass
substitution — an inserted value is never re-scanned, so state values full of `$` need no escaping
and cannot smuggle a reference in. ADR 016 §1a reserved this seat when it was accepted.

Prompt construction beyond interpolation — template libraries, parameterized inserts, per-model
instruction formatting — is the concern of registered components, possibly external modules, never
of this action: a registered function assembles the prompt into a parameter, and `${param.<name>}`
inserts it in one pass. This is the sanctioned channel for every prompt this decision does not
cover: the authored-file form `prompt_ref` and, behind it, an artifact-sourced prompt are deferred
to Leaves open until a scenario asks for them.

The action resolves the prompt, calls the adapter, parses the reply according to `format`, decodes
the declared values through their codecs, and returns an `ActionNodeOutput` whose `param_writes`
carry them and whose `output_text` is the raw reply. A reply that cannot be parsed or misses a
required value is an error value (`llm_answer_invalid`), which guards and transitions handle like
any other node error. The decoding step — the declared shape plus raw values in, typed writes or an
error out — is one code path shared with the ADR 013 answer binding, so the two declarations cannot
drift; the extraction of raw values from the reply (`format`) and the failure semantics stay the
action's own: an invalid reply is a routable error value here, where a refused answer in `ask`
changes nothing and re-presents. The action is automatic: the run does not pause.

The `llm` action is the automatic counterpart of the interactive `ask` (ADR 013): the two share the
answer declaration but sit on opposite sides of one boundary. `ask` binds an answer produced outside
the engine — the answerer initiates the resume, and the pause is the contract; it is built for the
human-in-the-loop archetype. `llm` is the second archetype, the autonomous model step: a call the
engine performs itself inside the run and audits itself. The core carries it as a dedicated action
rather than a convention over registered functions for three reasons: the node contract can require
the fields the journal must record (provider, model, status), the reply handling every provider
needs — parsing, typing through codecs, error classification — is written once instead of per
vendor module, and native model steps become a declared capability of the engine rather than an
installation's habit.

### 2. Provider adapters as registered components

An adapter is a callable registered under a new registration kind, `@register_provider`, with its
own registry — the fifth kind beside actions, functions, validators and codecs, following the
one-kind-one-registry pattern the core already has. A convention over `FUNCTION_REGISTRY` was
weighed and rejected: the help contract promises adapters their own component type, which over
functions becomes metadata guesswork; the signature would go unchecked at registration; and the
`providers` config section would resolve provider names against the function namespace. The
registry infrastructure of ADR 005 is generic, so the fifth kind costs a registry module, a loader
line and a help adapter.

The signature is fixed: an adapter receives the prompt, the model, the call options and the
provider configuration, and returns the reply text or an error value with an error class (§5). The
prompt crosses the signature as one text; how it becomes the provider's payload is the adapter's
business — a single user message for a chat endpoint, a system prompt, when needed, as an opaque
call option. Structured messages and conversation history are a later decision, taken when a
scenario shows them: the `llm` node holds no dialogue by construction, so a history would arrive as
a parameter, not as node state.

The core ships no provider adapter. The first real adapter is an external module (ADR 005
`external_modules`) speaking to a local model server — the route the POC took against LM Studio.
Which protocol it speaks is the module's decision, not the core's: the LM Studio API, whose model
management loads and unloads models with nothing running but an installed LM Studio; the generic
OpenAI-compatible HTTP protocol, which reaches compatible local servers and cloud models alike; or
both as variants of one module. The core fixes only the adapter signature and the error classes.
This keeps provider semantics — endpoints, auth headers, protocol drift — out of the core's release
cadence, and it exercises the plugin model with a real consumer, which nothing has done yet. The
module lives in this repository as its own package beside the engine — an officially supported
add-on, its layout a choice of the implementation and its productization deferred. The one adapter
the core does carry
is `fake` (§6): not a provider but the null implementation of the contract — no network, scripted
replies — so the action's own tests, the help surface of a bare install and the example workflows
stand without any plugin.

### 3. Provider configuration and secrets

The engine configuration file (ADR 008) gains a `providers` section: per provider name, the adapter
to use, its base URL, the default model, and the *name of the environment variable* holding the
credential — never the credential itself. A session records the provider and model each `llm` node
actually used in the journal event of the call, so a resumed or audited run knows which model
answered.

The provider block is **not** snapshotted into `session.json`. The ADR 004 snapshot solves a
bootstrap problem — without the storage record a resume cannot even find its state — which
providers do not have: they resolve at call time, when the engine configuration is already read.
The block is environment, not identity of the run: base URLs and credential variable names are
facts of one machine, and a snapshot would pin a moved session to the endpoints of the machine it
left, while ADR 003/008 keep state portable on purpose. Reproducibility is carried by the journal
instead — what actually answered is recorded per call, so a configuration change between calls is
visible rather than silent.

### 4. Audit as artifacts and events

Every call journals a session event (`llm_called`: node id, provider, model, status, error class,
token counts if the adapter reports them). Prompt and reply are written as artifacts under a
deterministic name (`<node_id>.prompt`, `<node_id>.reply`, attempt-numbered) when the node opts in
(`record: true`), so they can be declared deliverables or inspected after the run. Nothing new is
added to the state model.

### 5. Error classes, not retry policy

The adapter reports each failure as one of a fixed set of classes (`transient`, `rate_limited`,
`permanent`, `invalid_request`, `timeout`, `context_overflow`) which the action surfaces as the
node error code. This ADR does not decide delay or backoff: that is the retry-policy decision of
the recovery note (b), which will consume these classes. Until then the existing
`max_attempts`/self-loop allowance is the only retry.

`context_overflow` is deliberately split from `invalid_request`. The engine cannot count a model's
tokens — tokenizers are model-specific and the core carries none — so the provider's refusal is the
one honest overflow signal, and a guard that sees the class can route the run into a branch that
splits the data and loops the call per chunk. Chunking itself is that graph pattern, never the
action's hidden behaviour (alternative F).

### 6. Testing

The `fake` adapter ships with the core (§2) and returns scripted replies, so `llm` nodes are
covered by deterministic tests, a bare install registers one adapter on its help surface, and the
example workflows never call a network in `pytest`.

### 7. Three shared mechanisms with the question document

Session `2026-08-23-architecture-1` (G2) decoupled this decision from the question document of
ADR 019: the input of an `llm` node is a prompt — template text under ADR 016 — plus the answer
declaration of ADR 013, not a rendered question document; the document serves an answerer outside
the run. So that the two instruction channels cannot drift apart, three mechanisms are fixed as
shared, each written against an accepted ADR rather than against the other Draft:

- **One answer-shape generator.** The description of the expected answer — generated from the
  ADR 013 answer declaration and the value form each codec declares — is produced by one
  component. This decision does not put it into the prompt; if a scenario asks the prompt to state
  the answer's shape, the prompt consumes that generator, never a second assembly.
- **One template-file loader.** Any field that sources template text from an authored file is
  served by one loader beside the interpolation module; `prompt_ref` (Leaves open) is its first
  instance when a scenario brings it back.
- **`node.` is a prefix of the template-text contract.** If the ADR 016 contract gains a reference
  prefix over the node's own counters, it resolves on any node whose fields are template text —
  the `llm` prompt included — not as a property of `ask`.

### Open points

None. The six points this Draft carried were settled in session `2026-08-21-architecture-1`; the
change log records each.

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

### E. The model as the far end of an `ask` node
The fold this draft's former open point 6 asked to argue: no `llm` action — a model step is an
`ask` node, and an external driver script reads the published question through the ADR 018 read
surfaces, calls the model and answers with `resume --answer`. Everything it needs is already
accepted: typed answers (ADR 013), a post function to normalise the reply (ADR 015), interpolation
in the question text (ADR 016). Rejected on three grounds. First, every model call becomes a full
pause-and-resume round trip — process exit, an external invocation, engine bootstrap, state reload —
so a workflow of model steps is driven by the driver, not the engine. Second, the provider, the
model, the call options and the retries live in that driver: not versioned with the workflow
definition, not journaled, different on every installation — the definition no longer states which
model does the step. Third, the engine never sees a provider failure, so the error classes of §5
cannot exist and the retry policy of the recovery note (b) loses its input; a failed driver is
simply a resume that never comes. The boundary this keeps: `ask` is for an answer from outside the
engine's trust boundary, `llm` for a call the engine owns. A driver over `ask` remains possible for
a model that genuinely is outside (a human-supervised agent, a vendor UI) — it is a superstructure
over the engine, not the sanctioned mechanism of a model step.

### F. An abstract LLM action with chunking subclasses
Make `llm` an abstract base with overridable steps and ship typical chunking strategies as
subclasses. Rejected twice over. Extension in this architecture travels through registration, not
inheritance: an external module may already subclass the action and register its variant under its
own name — the point ADR 015 made as its alternative C — while declaring the base abstract would
sanction a second extension axis and couple plugins to the core's internals. And chunking cannot be
a method override at all: one node is one call and one journal event, so N chunks are N calls — a
loop in the graph, with a splitter function filling a parameter, the `llm` node visiting once per
chunk and an accumulating function collecting the replies, the accumulating pattern the engine
already carries. The splitters and accumulators are registered functions, natural neighbours of the
instruction-formatting module (Leaves open).

### G. A model-selecting `llm` action

Give the action a list of candidate models and let it pick an available or fitting one at call
time. Rejected: which model does a step is a decision of the flow, and flow decisions live in the
graph, made by guards in code and explained by their traces — selection inside the action is
hidden policy, and an availability fallback makes two runs on the same data differ for a reason no
trace records. Per-node `model` plus graph branching covers the tiering the scenarios need; if
run-time selection is ever needed, its deterministic form is recorded in Leaves open: a registered
function chooses and writes the model name into a parameter, and `model` resolves it as an
engine-resolved reference — the choice stays declared, coded and journaled.

## Consequences

- Enables: one node per model step, vendor-neutral workflows, typed model output on the bus, audit
  of every call, a place for credentials, and error classes a later retry policy can use.
- Costs: a new core action, a registration kind with its registry and help-contract adapter, a
  `providers` config section, two or three session event codes, the `fake` adapter in the core, and
  the provider-adapter package maintained in this repository as an external module.
- Closes off: vendor SDKs and provider adapters in the core (`fake` is the null implementation of
  the contract, not a provider); models as guards.
- Leaves open: retry/backoff (recovery note (b)); token or cost budgets next to the node cap
  (ADR 010) — not in scope until a run shows the need; `pre_functions`/`post_functions` — the
  call's own preparation and cleaning chains, cut by G1 until a scenario asks, their four settled
  semantics kept in the 2026-08-21 change log entry; `prompt_ref` — the authored-file form of the
  prompt, deferred until a scenario asks (the hand-build of `load-test-triage` measures it), served
  by the shared loader of §7 when it returns, with an artifact-sourced prompt as its later,
  separately decided case; the adapter package's protocol set and its productization; run-time
  model selection — the `model` field as an engine-resolved reference filled by a deterministic
  selection function, taken only if the `tiered` gate variant shows per-node models and graph
  branching insufficient (alternative G stays rejected); the
  instruction-formatting module the deferral protects — prompt template libraries and per-model
  formatting as external components, the same concern the question-rendering note holds on the
  `ask` side, with the chunking splitters and accumulators as its natural neighbours; and extending
  the template-file channel to the `ask` presentation fields.

## Related ADRs

- Depends on: ADR 005 (registration and external modules), ADR 006 (typed writes), ADR 008
  (configuration file), ADR 011 (artifacts), ADR 013 (answer declaration), ADR 016 (the template
  text contract the prompt inherits).
- Touches: ADR 002 (guards stay deterministic), ADR 004 (session record, if snapshotted), ADR 009
  (help contract gains a component type), ADR 012 (deferred question §1, narrowed by ADR 016),
  ADR 015 (the composition-inside-one-action pattern the cut chains would follow), ADR 019 (Draft;
  decoupled by G2, the shared mechanisms of §7).

## Implementation notes

The existing out-of-repository LM Studio POC is the reference for the adapter signature. No POC
under this ADR: the two questions one was meant to answer (former open points 1 and 6) were settled
on paper, point 1 largely by the accepted ADR 016. The freeze-gate evidence is the three class 4
variants named in Consumer. The variants keep to the surface this ADR owns: the `tiered` report
stays two deliverables — the CSV table and a proposal text written by a file function — so the
gate profits from the output-family ADR without depending on it; the splitter and accumulator of
the `chunked` variant are the generic bus work of G5, component work under ADR 006; prompts and
replies are recorded as artifacts (`record: true`).

Choices the feature branch makes, not this decision: where the decode function shared with the
ADR 013 answer binding lives, and the layout of the in-repository adapter package with its example
`external_modules` configuration and the protocol set it starts with.

## Change log

- 2026-08-19: opened as Draft in session `2026-08-19-architecture-1`.
- 2026-08-21: open point 6 settled in session `2026-08-21-architecture-1`: the dedicated `llm`
  action stays as the automatic counterpart of `ask`; the driver fold is recorded as rejected
  alternative E, and §1 gains the trust-boundary framing and the action-over-function rationale.
- 2026-08-21: open point 1 settled in the same session, mostly by ADR 016, which decided the
  in-text case after this draft was opened and reserved the prompt's seat in its §1a: the prompt
  inherits the template text contract whole. What the session added: `prompt_ref` narrows to an
  authored file, defined as a channel of the template-text field kind (one loader, `prompt` its
  only instance for now, the `ask` fields a later decision), read at node build so the two-failure
  contract holds; an artifact-sourced prompt and the instruction-formatting module move to Leaves
  open as deferred, with a registered function assembling into a parameter as the sanctioned
  channel meanwhile.
- 2026-08-21: open points 2 and 3 settled in the same session: the OpenAI-compatible adapter is the
  first external module, kept in this repository as the reference plugin, while the core ships only
  the `fake` null adapter; `@register_provider` is a real fifth registry rather than a convention
  over functions; and the adapter signature is fixed as text-in/text-out, with structured messages
  and history deferred until a scenario shows them.
- 2026-08-21: open points 4 and 5 settled in the same session: the provider block is not
  snapshotted into the session record — it is environment rather than run identity, providers have
  no bootstrap problem, and the per-call journal carries reproducibility; the codec decoding of the
  reply is one code path with the ADR 013 answer binding, while reply parsing and failure semantics
  stay the action's own. With all six points settled, the Draft is ready to enter Implementing; no
  POC is needed.
- 2026-08-21: amended in the same session after a follow-up discussion. §5 gains
  `context_overflow`, split from `invalid_request` so a guard can route an overflow into a chunking
  branch of the graph; §1 gains the optional `pre_functions`/`post_functions` chains — the call's
  own tooling, in the composition-inside-one-action shape the `functions` node already practises,
  with four semantics fixed: pre writes overlay the prompt resolution and leave in the node's
  single output, the post chain cleans the raw reply before parsing, a failing function is a
  routable node error value, and the audit artifacts bracket the provider call. An abstract action
  family with chunking subclasses is rejected as alternative F — chunking is a graph pattern over
  splitter and accumulator functions.
- 2026-08-24: narrowed in session `2026-08-24-architecture-1`, executing G1 and G2 of
  `2026-08-23-architecture-1`. Kept: the action with `format` parsing, the provider registry with
  the `fake` adapter, the `providers` configuration, the call audit and the error classes. Moved
  to Leaves open with their triggers: `pre_functions`/`post_functions` and `prompt_ref`. The
  `Consumer` section is added; §7 records the three mechanisms shared with the ADR 019 Draft — the
  answer-shape generator, the single template-file loader, `node.` as a contract prefix — so the
  two instruction channels cannot drift.
- 2026-08-24: revised in the same session at the owner's review. The personal freeze gate is
  decoupled from the phase exit: `Consumer` names the class 4 `described`/`tiered`/`chunked`
  variants of `folder-inventory-to-csv` as the gate evidence and `load-test-triage` as the phase
  consumer — the phase gates every ADR of the phase, so a per-ADR gate stays local and small. The
  adapter package's home is decided — this repository, an officially supported add-on — while its
  protocol set stays the module's own choice (the LM Studio API with model load and unload, the
  generic OpenAI-compatible HTTP that also reaches cloud models, or both); alternative G rejects a
  model-selecting action, with the deterministic selection form in Leaves open. The Implementing
  transition is deferred behind the output-family ADR that the operator's
  `result-file-composition` note opens (roadmap step 7).
