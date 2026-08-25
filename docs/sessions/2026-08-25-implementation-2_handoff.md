# Session note: 2026-08-25 implementation 2

## Type
`implementation`

## Goal
Give the `lmstudio` adapter the load-time settings its server's load endpoint actually accepts —
declared once in the provider block and forwarded unread — and correct the open question of
`2026-08-25-implementation-1`, which recorded those settings as having no channel at all after
assuming the endpoint rather than asking it.

This session was opened mid-branch, like the residency session before it, and runs on the same
branch, `feature/adr_014-llm-node-and-provider-adapter`. It comes before the gate variants because
it is what makes their `context_overflow` evidence a fact the server produces on request rather than
a window set by hand in an application.

## Completion criteria
- The provider block carries a load configuration inside its `options`, and every member of it
  reaches the load request unread, by the same rule that already keeps the chat call's options
  opaque: a setting the server gains later needs no release of this adapter.
- The model of a load stays the adapter's own: a `model` member inside that block cannot redirect
  the load, because ownership is what every release rule is built on.
- The settings apply to a load this adapter performs. A model the server already holds is used as it
  stands, whatever it was loaded with, and the adapter's help entry says so rather than leaving an
  operator to discover it.
- A load the server refuses because of a setting is classified by the same rule as every other load
  failure and is not raised.
- Tests against the scripted loopback server: the declared settings reach the load request, the
  block cannot redirect the model, a refusal of a setting is a classified failure, and an absent or
  empty block loads exactly as before.
- A by-hand run against the real server: a model loaded with the context window the block names,
  read back from the server, and a prompt that overflows that window while the same prompt fits the
  default one.
- ADR 014 §2 and its change log record the load configuration; `example_config.json` shows it; the
  help entry of the adapter names it among its configuration keys.
- The open question of `2026-08-25-implementation-1` is corrected where it stands, with a pointer to
  the session that answered it, so a wrong fact does not keep standing in the trail.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No core change: the provider contract, the seat, the `llm` action and the six error classes stay
  as ADR 014 delivered them. The configuration the server can echo back on a load is deliberately
  not carried into the reply — the contract has no channel for it, and widening the contract is a
  decision, not an implementation detail.
- No per-node load settings: a node cannot ask for its own context window. Two windows for one model
  means two provider blocks, which is the indirection the provider name already is.
- No reload of a model the server already holds in order to change what it was loaded with.
- No change to `openai_compatible` — **widened during the session, see decision 4**: the load
  endpoint stays the product's, but the classification of an oversized prompt was corrected there,
  because the by-hand run this session owes produced the first real overflow and showed the shared
  classifier missing it.
- No gate variants and no documentation set; both belong to the sessions after this one.

## Status
`completed`

## Result
All completion criteria are met.

- `src/workflow_engine_providers/lmstudio.py`: the provider block's `options` gains `load_config`,
  an object whose members reach the load request unread. The model is written into the request last,
  so a load configuration cannot redirect the load onto another model - the ownership every release
  rule rests on. The block governs a load the adapter performs and nothing else, and the help entry
  says so beside its other notes.
- The adapter's help entry names `load_config` among its configuration keys, `example_config.json`
  shows it beside `load_timeout`, and ADR 014 §2 carries the decision with its change log entry.
- Five tests in `tests/test_adr014_lmstudio_adapter.py`, against the loopback server, which now
  validates its load request as the real one does: the declared settings arrive, a block without a
  configuration loads exactly as before, a `model` member cannot redirect the load, a setting the
  server refuses is a classified failure with no call made, and a model the server already holds is
  used as it stands. Two cases joined the overflow parametrization of
  `tests/test_adr014_adapter_package.py`. `uv run pytest` 716 passed, `uv run ruff check .` clean,
  `uv run ruff format .` applied.
- The open question of `2026-08-25-implementation-1` is corrected where it stands rather than
  rewritten, with a pointer to this session.

What ran by hand against the real server, one prompt of 24522 tokens against two declared windows:
under `context_length: 4096` the server refused it, naming the window it had been given; under
`context_length: 32768` the same prompt was answered, and the record of the visit carries the model,
the provider and the 24522 tokens the server counted. The window is therefore what the provider
block says, measured rather than reported. Both runs ended with the model released by `finalize`,
the failed one included, and the server's own listing read empty after each. The documented load
configuration of the product — a context length, a batch size, flash attention, an expert count, a
KV-cache placement — is engine-dependent: several of its members exist only for a model running
under one of the product's engines, which is the measured argument for forwarding the block rather
than enumerating it. A load asked to echo its configuration returns the whole of it, and the model
listing reports the same configuration for every resident instance.

## Decisions
1. **The load configuration is forwarded unread rather than enumerated key by key.** The
   alternative — the adapter naming the settings it knows and passing only those — buys a typo
   caught locally and costs a release of this adapter for every setting the server adds. It is also
   wrong on its own terms: the product's documented set is engine-dependent, so an enumeration would
   name members that do not exist for a model running under a different engine. Unread, a member
   nobody knows is refused by the server and arrives as a classified failure, which reports the
   mistake without inventing a rule about someone else's API.
2. **It lives in the provider block and never on the node.** A context window is a fact about the
   machine that holds the model, and a workflow definition travels between installations. The node
   keeps its opaque call options for what one step needs; two windows for one model means two
   provider blocks, which is what a provider name already is. The cost is named rather than hidden:
   a node cannot ask for a bigger window for one heavy call.
3. **The configuration governs a load this adapter performs and nothing else.** A model the server
   already holds is used as it stands. Re-loading it to impose the block's window would evict what
   someone else is working with, which is decision 2 of the residency session read the other way
   round, and a run must not produce that surprise.
4. **The overflow markers gained the wording a real server actually uses, and this session's scope
   was widened by one boundary to do it.** The by-hand run produced the first overflow the engine
   could ask for on demand, and it came back `invalid_request`: the server refuses with `exceeds the
   available context size`, under an error type of the same word, while every marker written before
   this session named the *length* or the *window*. The class ADR 014 §5 calls the one honest
   overflow signal therefore never fired against that server, and the `chunked` gate variant of the
   next session is built on exactly that class. Deferring the two markers to a session of their own
   was weighed and rejected: the defect is the direct product of what this session made possible,
   the fix is two markers and two test cases, and the boundary that forbade it is amended in the
   open rather than quietly stepped over.
5. **The corrected open question is left standing with its correction beneath it.** Deleting the
   wrong claim would leave the trail reading as if it had never been believed. A session note records
   what was known and when, so the claim stays and the correction names the session that measured it.

## Open questions
- The model listing reports the load configuration of every resident instance, so an adapter could
  know the window of a model it did not load. Nothing was built on it: the provider contract has no
  channel for carrying it into the reply, and the one use that suggests itself — re-loading a model
  whose window is too small — is exactly the eviction decision 3 refuses. It becomes a question the
  moment a scenario needs a run to act on the window it was given.
- A `load_config` written into a node's call options reaches the chat body as a field and the server
  refuses the call. Loud rather than silent is the right direction, but the report then names the
  chat call instead of the mistake. Whether the adapter should refuse it when the node is built is
  open.
- The overflow class is still told apart by a substring of an error body. This session added the
  third vocabulary a server has used for one condition; the next server with a fourth misses again,
  and a missed marker costs a run the branch that would have split its data. Whether the class
  deserves a signal that is not a substring belongs to the ADR that owns the class set, beside the
  seventh-class question the residency session raised.
- The action-registry twin of the provider-registry bug, carried from `2026-08-24-implementation-5`
  and still unowned.

## Next steps
1. Session B on this branch, whose note is already written as `2026-08-25-implementation-3`: the
   `described`, `tiered` and `chunked` variants of `folder-inventory-to-csv` as the class 4 evidence
   of ADR 014. Its `chunked` variant can now produce a real `context_overflow` on demand by naming a
   small window in the provider block.
2. The closing session of the branch: the documentation set, the merge and the freeze gate.
3. Decide the action-registry twin: a `fix/` branch of its own, or a session that already touches
   the registries.

## References
- Branch: `feature/adr_014-llm-node-and-provider-adapter`.
- Code changed: `src/workflow_engine_providers/lmstudio.py`,
  `src/workflow_engine_providers/openai_compatible.py` (the overflow markers of decision 4),
  `src/workflow_engine_providers/example_config.json`.
- Tests: `tests/test_adr014_lmstudio_adapter.py`, `tests/test_adr014_adapter_package.py`.
- Documents changed: `docs/adr/adr-014-llm-node-and-provider-adapter.md`,
  `docs/sessions/2026-08-25-implementation-1_handoff.md` (its open question corrected), this note.
- Preceding note: `2026-08-25-implementation-1_handoff.md`.
- Related ADRs: ADR 014 (implemented here), ADR 005, ADR 008, ADR 009.
