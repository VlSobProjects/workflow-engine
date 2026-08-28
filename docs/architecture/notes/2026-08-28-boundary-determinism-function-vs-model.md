# Determinism of the boundary, not the step: the function-versus-model choice

- **Date:** 2026-08-28
- **Trigger:** external talk with an AI practitioner (2026-08-28); the question "where is the line
  between a very complex deterministic function and a model that could do the same?"
- **Status:** open
- **Affected:** ADR 002, ADR 014, ADR 021, guards (`docs/architecture/overview.md`)

## The resolution of the dilemma

The engine does not require the *step* to be deterministic — only the *boundary*. A step may be a
strong model with a prompt (a pseudo-deterministic step): its answer is normalized by a
post-function, and the normalized output is routed by deterministic guards. The transition is
deterministic over the normalized output regardless of who produced it; the guard does not care
whether a function or a model answered.

This reframes "complex function vs model" from an architectural question into an engineering
trade-off, and a reversible one:

- A function is testable and free to run, but expensive to write against messy, highly variable
  input.
- A model is cheap to author, but paid on every run and needs normalization plus a guard at the
  boundary.

Because a step is swappable in place, the choice can be revisited with evidence: start with a model,
let the journal (ADR 021 record channel, model call records) accumulate real inputs and outputs, and
decide from that data whether replacing the model with a function pays off. **The journal becomes the
specification of the future function** — and the replacement can be verified on the same data.

## Open questions

- Is anything missing in the engine, or is this purely an authoring pattern? Composition today would
  be an `llm` node (ADR 014) followed by a function node that normalizes — is a dedicated
  post-normalization hook on the model step worth anything, or is the two-node shape exactly right
  (one action per node, ADR 002)?
- Does the journal actually capture enough to serve as a replacement specification (full prompt,
  full raw answer, normalized value), or does that claim need a check against ADR 021?
- Where should the pattern be documented for authors once it stabilizes — an example walkthrough, or
  authoring guidance in phase 3 surfaces?
