# The answer document has one form, and the question does not publish it

- **Date:** 2026-08-21
- **Trigger:** session `2026-08-21-investigation-2`: the ADR-0083 scenario was driven by hand, one
  question at a time, from a runtime root outside the repository. Both findings below were noticed
  from the answerer's seat rather than derived from the contract
- **Status:** open
- **Affected:** ADR 013 (§3 the published question block, §4 the answer document, alternative F),
  ADR 005 (a registered answer format would be a component it loads), ADR 009 (the help payloads are
  the other place a fixed contract could be published once),
  `2026-08-20-question-rendering-for-an-audience.md` (the same question in the outbound direction),
  `2026-08-21-agent-instruction-and-skill.md` (what the instruction has to carry because the block
  does not)

## Two findings, one boundary

**1. The block publishes what to answer, never how to answer it.** The published block carries the
node, the presentation fields, the declared `answer` names and types, the error catalogue and the
generic error code. The envelope those fields travel in — `status`, `values`, `text`, `error_code`,
`message`, `actor` — is decided in ADR 013 §4, implemented in `answers.py`, documented in `README.md`
("Answering an interactive workflow") and `docs/architecture/overview.md`, and named in one line of
the `--answer` help. It is not in the block.

The split is visible inside a single field: `generic_error_code` is published, and the field that
code goes into is not. Half of "how to answer" crosses the publishing boundary and half stays behind
it.

The consequence is concrete: an answerer holding only the paused command result cannot compose a
valid answer. It has to have been told the envelope beforehand, by a human or by a document handed to
it. That may well be the right design — but nobody decided it. ADR 013 §3 enumerates what the block
carries and never asks whether the return form belongs there.

**2. `node_id` is in the block and no answerer can use it.** `resume` addresses a session; there is no
way to answer a named node, so the node id cannot change what an answerer sends. It serves a caller
that dispatches questions to different handlers, or one keeping its own log — an orchestrator's
field, sitting inside the answerer's document. It is the smallest concrete instance of the block
serving two readers at once.

## The direction nobody asked about

The rendering note argues the outbound side: one structured block, many audiences, a registered
renderer per audience, the audience chosen by the consumer rather than by the node. Its scheme stops
at `renderer(QuestionBlock) → str`.

The return channel has no counterpart. One JSON shape for every answerer — a human at a terminal, a
large model, a small local one, a program — fixed in the core, not configurable and not per workflow.
Checked before writing this, because it felt like something already decided:

- ADR 013 §4 decides the shape and rejects the flag form (alternative F). One format, no template, no
  per-workflow field naming, no hook for an external one.
- The rendering note is a note, not a decision, is `open`, and covers the question only.
- The only renderer in the tree is a hardcoded class over the internal `PresentResponse`, reached by
  one test's `print` — the very input the rendering note's own fixed point rules out for a renderer.

So the answer side is unrecorded rather than settled, and this note is its first record.

## Options, none free

- **Publish the envelope inside the block.** The block becomes self-sufficient; the cost is the same
  fixed document repeated in every paused result — see
  `2026-08-21-command-result-cost-for-a-machine-reader.md`.
- **Publish it once, machine-readably, beside the help payloads (ADR 009).** `help-component ask`
  today describes the node for an author, not the exchange for an answerer; a fixed contract fetched
  once fits that family better than a per-question repetition.
- **Leave it to the instruction or the Skill.** Cheapest, and it forces
  `2026-08-21-agent-instruction-and-skill.md` to state plainly that the block is not self-sufficient
  by design, which is the opposite of what its measurement currently assumes.
- **A registered answer format, symmetric to the renderer.** The largest, and not the mirror image it
  looks like: a formatter that gets something wrong produces an ugly sentence, a parser that gets
  something wrong decides what reaches the state, so an external answer format is a failure surface
  in a way an external question format is not.

## What this note does not claim

The flow driven here is the synthetic ADR-0083 coverage scenario, whose purpose is to touch every
node type. Its wording — the self-directed follow-up question in particular — is not evidence about
any use case, and nothing here is a complaint about it. One engine-level property did show through
while answering it: **a bound the author sets is invisible to the answerer.** The `minimum` of a
collecting loop and the `max_attempts` of a re-ask are both real constraints the answerer is judged
against and cannot see, so "I have nothing more to ask" has to be sent as a declared refusal. That is
the same class as item 2 of the agent-instruction note, arriving from a second direction.
