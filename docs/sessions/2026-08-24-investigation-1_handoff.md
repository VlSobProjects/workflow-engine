# Session note: 2026-08-24 investigation 1

## Type
`investigation`

## Goal
Size the implementation of ADR 014 against the code that exists, and decide how it is split, how it
is branched, and who owns the journal question its §4 raises.

## Completion criteria
- The implementation surface of ADR 014 is enumerated against the current code, not against the ADR
  text alone.
- The session split and the branch shape are decided.
- The audit requirement of §4 is diagnosed against what the engine records today, and given an owner.
- The next steps are recorded in order.

## Scope boundaries
- No code changed. ADR 014 stays `Draft` and its body is untouched.
- No ADR 021 body written here: this session decides that it exists and what it must weigh, not what
  it decides.
- Only step 8 of the roadmap is rewritten; no step is renumbered and no other step is touched.

## Status
`completed`

## Result
The implementation surface of ADR 014, measured against the code:

- A fifth registration kind with its own registry, and its ripple through the places that assume
  four: the help component type and its collection key, two spots in the help builder, a new help
  adapter, the component loader's core/external split, and the core module manifest.
- The adapter contract — one signature and the fixed error classes of §5 — and the `fake` adapter.
- A `providers` section in the engine configuration, not snapshotted into the session record.
- The `llm` action, comparable in size to the 273-line `ask` action it is the counterpart of, plus
  the decode path shared with the ADR 013 answer binding.
- The call audit of §4.
- The provider-adapter package kept in this repository, with its own tests and configuration example.
- The three class 4 gate variants, of which `chunked` also needs the splitter and accumulator
  functions the ADR calls generic bus work.
- The documentation set: the ADR body under what was delivered, the walkthroughs, the scenario
  registry, `README.md` and the architecture overview.

That is three to four times the last implementation session and does not fit one context. Sized as
four sessions: the provider seat; the `llm` action with its audit; the adapter package with the
by-hand run against a local model; the three gate variants with the documentation and the freeze.

Findings behind the journal diagnosis:

1. **Node execution is not journaled today.** The session journal holds lifecycle events only —
   session created, workflow started, inputs set, answered, resumed, paused, completed, failed,
   deliverable missing, artifacts exported. A node that ran successfully leaves no row.
2. **The per-node slots of the state hold the latest visit, not a history.** The output text, the
   error, the guard results and the visit counter are all overwritten on the next visit. In a loop —
   which is exactly the `chunked` gate variant, one visit per chunk — the provider, the model and
   the status of every earlier call would survive nowhere.
3. **An action cannot write the journal.** It receives a read-only state view, returns one output,
   and the engine applies and saves it. A direct write would mutate the state outside that path and
   would leave records for outputs the engine never applied, because the write would happen before
   the transition is chosen.
4. **The journal is serialized inside the state file, which is rewritten whole on every save**, and
   the engine saves several times per node. Today that is safe because the events are few and are
   lifecycle only. Per-visit records change the regime: the list grows and the whole file is
   rewritten at every step.

## Decisions
1. **ADR 014 is implemented as four sessions on one branch, merged once.** The alternative — one
   branch per session, each merged into `development` — was rejected: it forces session boundaries
   by readiness rather than by volume and logical boundary, and when a slice does not reach that
   readiness it leaves only the choice between merging unfinished work and overrunning the session.
   One branch also matches the ADR process literally: one merge, one freeze-gate check over the
   whole surface. Every commit inside the branch still leaves the tests and the linter green, so the
   branch stays bisectable.
2. **The channel that carries a record from a node into the session's trail becomes its own
   decision**, opened as Draft ADR 021 and implemented before ADR 014, instead of a narrow
   `llm`-only field added inside ADR 014. Finding 4 is why the order matters: the destination
   question is real, and deciding it after model-call records already flow into the session journal
   would mean migrating them.
3. **ADR 021 must weigh at least four destinations**: the existing session journal; a separate
   record list inside the state; an append-only file outside the state; artifacts under ADR 011. It
   must also settle how the new stream meets the bounded read surface of ADR 018, which today serves
   the journal with a node filter and a tail bound.
4. **The consumer of ADR 021 is the first thing its session settles.** The first real consumer of
   node records is the model-call audit, which arrives only with the ADR 014 gate variants. So
   ADR 021 either stays `Implementing` until those land, or names its own class 2 or class 4
   evidence — otherwise the decision is unfreezable by construction.
5. **Roadmap step 8 is rewritten to carry both**, in order, without renumbering the steps after it.
   The order is what this session decided; the shape of the new decision is not, and the step says
   no more than the order.

## Open questions
- Where a node record lives — the four destinations of decision 3. Owned by ADR 021.
- Whether the freeze of ADR 021 waits on the ADR 014 gate variants, or whether it carries its own
  scenario evidence.
- Whether ADR 021 and roadmap step 9 — the atomic state write and the session lock — are one
  concern of the same file layer, and should be decided together.

## Next steps
1. Architecture session on `development`: open Draft ADR 021, decide the destination against the
   four alternatives and the consumer against decision 4.
2. Implement ADR 021 in its own branch and merge it.
3. Move ADR 014 to `Implementing`, open `feature/adr_014-llm-node-and-provider-adapter`, and run the
   four sessions sized above on that one branch.

## References
- Branch: `development`.
- Code read, not changed: the registries and the component loader, the help contract builder and its
  adapters, the configuration loader, the state model and its session events, the engine step loop,
  the action output, the `ask` action and the answer binding.
- Documents: `docs/architecture/roadmap.md` (step 8 rewritten), this note.
- Related ADRs: ADR 014 (`Draft`, untouched), ADR 013, ADR 018, ADR 011, ADR 006, ADR 009, ADR 005.
