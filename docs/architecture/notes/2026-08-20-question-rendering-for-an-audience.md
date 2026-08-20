# Rendering the published question for its audience

- **Date:** 2026-08-20
- **Trigger:** session `2026-08-20-architecture-3`: while deciding reference interpolation (ADR 016),
  the discussion separated the *content* of a question from its *form* — and the form side, which the
  interpolation evidence does not cover, is captured here instead of being decided on no evidence
- **Status:** open
- **Affected:** ADR 005 (a registered renderer is a component it loads), ADR 013 (§3, the
  published question block), ADR 009 (help contract), ADR 014
  (provider adapters format prompts for their model), the publishing-boundary note
  (`2026-08-19-interactive-exchange-publishing-boundary.md`, §1 and §3)

## The idea

One structured question block, many readers: a human wants prose, a small local model wants a short
prompt inside a small context window, a large model wants the format its vendor recommends, and what
suits one human is awful for another. Today every consumer formats the block itself (the CLI for a
human, a driver script for a model), and none of that formatting is shared, registered or
configurable.

The proposal that survived the discussion: a **renderer** — a registered function that takes the
published question and produces the text for one audience. Registered like every other component
(ADR 005), so formats can be added and configured without touching the core; selectable per
audience, so one flow serves an operator today and a model tomorrow.

## The scheme

```
AskAction → PresentResponse            (internal, unchanged)
          → QuestionBlock              (typed public class — the ADR 013 §3 contract, today an
                                        undocumented dict shape inside answers.question_block;
                                        serializes to data.question, restores from it)
          → renderer(QuestionBlock) → str   (registered function; one per audience/format)
```

Fixed points, argued in the session:

- **The renderer's input is the question block, not `PresentResponse`.** The internal class carries
  budget stops, failures and completion, and the publishing-boundary note §1 already warns that it
  "still looks publishable"; a registered function consuming it would freeze an internal class as a
  public API by use. The block is the already-published contract, and if a renderer misses something
  the block does not carry, that is a defect of the block's contract, to be fixed there.
- **The block becomes a typed, documented class.** A template author writes against described fields,
  not against a dict with bare keys. This is the "split the class" option of the publishing-boundary
  note §1 with its first real consumer, and the natural place for the block's `schema_version`
  (note §3).
- **The renderer is a pure formatter: no state, no writes.** It runs on every re-present, so it must
  be harmless to re-run; its input surface enforces that structurally.
- **The audience chooses the template, not the node.** ADR 013 §1: the answerer is a property of the
  answer, not of the node — the same flow is answered by an operator today and an agent tomorrow, so
  the selection belongs to the consumer side (session, configuration, driver), at most hinted by the
  node.
- **The rendered form is additive.** `data.question` stays the machine contract; a rendered text is
  produced beside it or by the consumer, never instead of it.

## Open

- Where rendering executes: the engine publishes a rendered form next to the block, or the consumer
  renders the block itself (both work over the same typed class; the engine-side form needs a
  decision about what appears in `data`).
- Whether the block's version is its own `schema_version` or the ADR 009 `contract_version` raised to
  cover it (publishing-boundary note §3 — decide together with the typing, not separately).
- What the audience registry looks like: named renderers selected in configuration, per session or
  per caller.

## Considered and rejected — recorded so the next reader does not retry it

- **A full-context processor** — a registered component that receives the state (or has
  `StateReadOnlyView` embedded in the block) and *generates* the instruction. Rejected three times in
  one week in three shapes: the pre-function (ADR 015 §1), the renderer-with-state, and
  state-in-the-block. The reasons do not change with the door: a plain `resume` re-presents the
  question and must not run code whose effects the engine cannot check (ADR 013 §6); the block is a
  disclosure boundary, and embedding state shows every answerer the whole bus, machine paths
  included; the journal records the block, so a prompt built from state the block does not carry is
  not reconstructible from the run's record; and the question's content stops being readable from
  the workflow definition. The state reaches a question through declaration — interpolation
  (ADR 016) — and through nothing else.
- **Trigger to reconsider:** a real flow in which a question must be *computed* rather than composed —
  one that declaration and interpolation cannot express. None exists; the ADR-0083 flow needed
  neither.

## Where this goes when it ripens

One ADR covering the typed block, its version and the renderer together — they are one decision
about publishing the question, not three. Its evidence arrives with the first two real audiences:
the CLI's human output and one model driver (ADR 014's adapters are the natural second consumer).
