# What a paused command result costs its machine reader

- **Date:** 2026-08-21
- **Trigger:** session `2026-08-21-investigation-2`: the ADR-0083 scenario driven by hand, with the
  paused JSON read the way an answering model receives it — as context it pays for
- **Status:** promoted → ADR 019
- **Affected:** ADR 007 (the CLI contract owns the command result shape), ADR 013 (§3 the published
  question block), ADR 018 (the read surfaces, which chose one shape per command),
  `2026-08-20-question-rendering-for-an-audience.md` (the typed block is the natural carrier of a
  split), `2026-08-21-answer-document-and-its-audience.md` (the other half of the same boundary)

## What one paused result actually carries

- **The instruction text, three times:** the result `message`, the block's `description` and the
  block's `instruction`. The chain is mechanical — `ask` defaults `description` to `instruction`, the
  CLI sets the result message from `description`, and the block prints both. An author who writes a
  real `description` gets two distinct texts and one copy; the floor is two, and no author choice
  removes it.
- **The status, three times:** the command status, the workflow status and the last event code, each
  in its own vocabulary.
- **The node id twice** (`data.current_node` and the block's `node_id`), **the session id twice**
  (top level, and again inside the work directory path).
- **Session-constant fields, resent every turn:** the flow id, the schema version, the work directory
  and the declared deliverables.
- **Empty fields, always printed:** the error map, the artifact map, the input list and a zero node
  limit. The JSON presenter serializes the whole result object; nothing is elided for being empty or
  default.
- **A timestamp that does not move.** `data.timestamp` is the state's creation time, not the moment
  the answer was produced: two consecutive turns of one session carry the identical value to the
  microsecond. A field that reads as "when this was produced" and is not.

## Why it is a contract question rather than tidying

The same document serves three readers: an operator watching a run, a program orchestrating it, and a
model that has to answer it. For the first two the repetition is harmless and occasionally useful. For
the third every repeated field is context it pays for, on every turn of an interactive flow — and an
interactive flow is exactly the shape that turns one run into many results.

ADR 007 fixed the command result and ADR 013 fixed the block. Neither states who the payload is
addressed to, or what a caller may rely on being present. So there is no ground on which a field can
be dropped today: silence is not permission.

## Options

- **Stop `description` defaulting into the result message.** The smallest change with a visible
  effect, and it is author-facing rather than contractual.
- **Omit empty and default-valued fields.** Cheap in code, and a contract change for anyone reading
  keys positionally.
- **Separate the answerer's document from the operator's telemetry.** The honest fix, and the typed
  question block proposed by the rendering note is the natural place to put the line.
- **Leave it and let the consumer strip what it does not need.** Today's de facto answer, worth
  writing down as a choice if it stays.

## Not measured

The counting above is of fields, not of tokens: no token measurement was made, and none of the
options was costed. That is deliberate — the finding is that the payload has no stated audience, and
the size is only what made it visible.
