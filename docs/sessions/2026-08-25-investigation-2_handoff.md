# Session 2026-08-25-investigation-2

## Type
investigation

## Goal
Confirm against a live local server that the per-server residency registry of
`2026-08-25-implementation-9` behaves as the scripted server says it does, since the gap it closes
was found by polling a real server and nothing but a real server can close it.

## Completion criteria
- The cross-block swap is observed on the server: two provider blocks of one run, two models, and
  the first released at the moment the second is loaded rather than both sitting resident.
- A second block declaring another context length is observed getting its own load rather than the
  resident instance of the first block.
- `release_foreign: true` is observed emptying the server of a model loaded by hand from the
  application before the run's first call, and the run's own load following it.
- Each observation is recorded in this note as a fact, with what was measured and how; a divergence
  from the tested behaviour is recorded as a defect and left to its own `fix/` session.
- The instrument — the engine configuration with the provider blocks and the throwaway
  definitions — stays outside the repository.

## Scope boundaries
- No code change: this session measures. A defect it finds is written down, not fixed here.
- No model quality, no timing harness: what is measured is residency, so the prompts are trivial and
  the models are the cheapest installed ones.
- The `reorganize-folder` example, the scenarios and the roadmap steps 14-15 stay untouched.

## Status
`completed`

## Result
Every rule of the fix holds against the live server, measured by polling the model listing four
times a second while a run worked, and one adjacent defect was found that no scripted server could
show. The instrument was four throwaway definitions and one engine configuration outside the
repository: two `llm` nodes on two provider blocks of one server, the same pair with two context
lengths of one model, a single node under a widened block, and a two-call flow with an `ask` between
the calls. Three small local models of different families served as the load; no code changed, so
neither pytest nor ruff was run.

### The cross-block swap, confirmed
Two blocks, two models, one server: the first model was resident from second 6, gone at second 14,
and the second model loaded at second 15; both were gone when the run ended. No sample of the poll
ever showed two models resident at once — which is exactly what `2026-08-25-implementation-8`
observed happening before the fix.

### A block's context length reaching the server, confirmed
Two blocks naming one model, one at 4096 and one at 16384: the poll showed the instance released and
re-loaded between the two calls, and the second call — a prompt of ~31,700 characters — was answered
rather than refused. The control run makes that decisive: the same prompt sent through the 4096
block alone fails, and the ADR 021 record names the class, `context_overflow`. So the second block
was answered by an instance loaded under its own settings and not by the first block's.

### The ownership rule, unchanged
A model loaded by a process outside the run stayed resident through a whole two-block run, while the
run's own models swapped beside it and were released at the end. Under `release_foreign: true` the
same foreign model was gone before the run's own model appeared, and the server was empty when the
run finished.

### The defect: a resumed run releases nothing it did not load
A flow of `llm` → `ask` → `llm` on one provider was run to the pause, then resumed to completion.
The model was resident during the pause, as ADR 014 §2 intends — the answer is expected shortly and
a release would buy an unload and a reload for nothing. **It was still resident after the resumed
run completed.** The residency memory lives in a process; the resuming process starts empty, sees a
model it did not load, and by the ownership rule leaves it alone — for ever. Every interactive
workflow with a model call therefore leaks one resident model per run, on the normal path rather
than on a crash.

This is older than the fix: the memory was per process before it was per server, so the same hole
was there with the per-block memory. It is recorded here rather than fixed, per this session's
scope.

### The configuration the leak does not survive
Measured after the note was first closed, on the same instrument and belonging to the same subject:
the leak does not happen when the provider block carries `release_foreign: true`. The same paused
flow was run under a widened block and polled twelve times a second. The model left by the pause was
released 0.11 seconds before it was loaded again, and the server was empty when the resumed run
completed. The mechanism is the clearing: the resuming process empties the server at its first
residency check, so the model it then loads is its own, and what it owns it releases. A poll four
times a second missed that window entirely, which is why the finer one was run.

This depends on decision 2 of `2026-08-25-implementation-9`, that the clearing happens before the
run's first residency *check* rather than before its first *load*. Before the first load it would
not fire at all here, because the resumed run would find the model already resident.

What makes this more than a curiosity is which constraint actually binds a local model. It is the
memory of the GPU, not the seconds a load costs: a model that does not fit the card runs an order of
magnitude slower, so a run that uses local models is scheduled for a window when the card is free of
other applications' models anyway. In that setting a block declaring the machine its own is the
normal configuration rather than an aggressive one, and it is today the only configuration under
which an `ask` node and an `llm` node calling a local model combine without leaving a model
resident. The reload it costs is noise beside the constraint it protects.

It remains a workaround, and for two reasons. An installation that must leave another application's
model alone cannot set the option, and there the leak stays. And nothing in the operator
documentation connects the option to the leak, so the combination is only findable by reading this
note.

## Decisions
1. **The fix of `2026-08-25-implementation-9` is confirmed live and needs no follow-up.** All three
   rules behaved on the real server as the scripted one says, including the one signal a scripted
   server cannot give: a real context window refusing a prompt that the wider one accepts.
2. **The resume defect gets its own session, and its shape is a decision, not an obvious fix.** Three
   routes, none free: let a paused session record what it left resident so the resume adopts it
   after re-checking the server, which keeps the pause optimisation but puts a residency fact into
   the session record; release on `PAUSED` after all, which costs an unload and a reload per
   question and contradicts ADR 014 §2 as written; or leave it to the operator through a release
   surface, which makes a leak the operator's routine. The first looks right and is the most work.
   The measured workaround weakens the second route's objection rather than the defect: where the
   load time is noise beside the memory of the card, releasing on a pause costs little, and that is
   the ordinary case for a local model.
3. **The defect is documented in this phase and fixed in a phase to be chosen.** It has a
   configuration that avoids it — one that a local-model installation would plausibly set anyway —
   so it blocks neither the phase 2 exit scenario nor the work before it. Which phase carries the
   fix is left open rather than assumed.
4. **The measured facts about the load listing are worth keeping**: the server's model listing names
   loaded instances but reports no context length for them, so what a resident instance was loaded
   with is not observable from outside the adapter. The overflow control is the only way to measure
   a window from the outside, which is why it is the instrument used here.

## Open questions
- Whether a session record is the right place for what a run left resident, given ADR 004 keeps the
  provider block out of `session.json` on purpose: what a run holds is not its identity either, but
  it is not the environment's fact either.
- Whether the operator documentation should name the configuration that avoids the leak while the
  defect stands, and where — the adapter's registered notes reach an operator listing components,
  `README.md` reaches one reading about the model call, and both would describe a defect in shipped
  documentation.
- Whether the same leak exists for any other resource an adapter may hold across a pause. Today
  `lmstudio` is the only adapter that holds one.
- The three questions of `2026-08-25-implementation-8` remain untouched: a node-scoped call timeout,
  a retry route that distinguishes a deterministic `llm_answer_invalid`, and where the small-model
  pattern is documented.

## Next steps
1. Roadmap step 14: the data-generation discussion, then the generators and the drift-B protocol.
2. The `fix/` session for the resume defect, opened by deciding between the three routes above and
   by placing it in a phase; until it lands, `release_foreign: true` is what makes an `ask` node and
   a local model call combine cleanly.

## References
- Branch: `docs/lmstudio-residency-live-check`
- ADRs: ADR 014 (`llm` node, provider adapters), §2 for the residency rules; ADR 021 for the record
  channel that named the overflow class
- Sessions: `2026-08-25-implementation-9` (the fix), `2026-08-25-implementation-8` (the rehearsal
  that found the gap)
- Documents changed: this note only, extended once after it was closed with the measurement of the
  configuration the leak does not survive
