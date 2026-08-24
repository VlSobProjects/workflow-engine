# The operator cannot read the flat output of a run

- **Date:** 2026-08-24
- **Trigger:** session `2026-08-24-architecture-1`: while choosing the freeze-gate consumer for
  ADR 014, the owner, as the operator of the shipped scenarios, named the output surface the weak
  one — ahead of any LLM work
- **Status:** open
- **Affected:** ADR 011 (artifacts and export), ADR 016 (template text confined to the `ask`
  fields), ADR 006 (what a function writes to the bus), gap G6 of `2026-08-23-architecture-1`,
  `2026-08-21-support-intake-use-case.md` (gaps 2 and 3), scenario `load-test-triage` (open
  decision 4)

## The report

The inventory examples export one flat table over every file of the walked tree. For a human that
is practically unreadable. The wanted shape, stated concretely: one table per folder, the folder
path as its heading, the rows carrying the file name and its per-file fields — a composed
document, not a bigger table.

## The measurement

What the core does today: render one table shape (in six syntaxes), write fixed text through file
functions, export artifacts under configuration-time names. What it cannot: compose a result file
from run values — no template text outside the `ask` presentation fields, no document artifact of
an author-declared shape, no artifact name carrying a run value (G6; `support-intake` gaps 2
and 3). Every new output form today is one more hardcoded function — the sediment the function
inventory already shows.

## Why this is ripe now

G6 was deferred with the trigger "when the exit scenario needs its handover" — that is, until
consumer evidence exists. The evidence arrived earlier and from a live consumer: the operator
reading the deliverables of the shipped scenarios. The LLM work ahead — the ADR 014 gate variants
and the `load-test-triage` report — produces text that lands in these same outputs, so the output
family pays off before the `llm` node exists and keeps paying after.

## Feeds

Roadmap step 7: the architecture session that opens the output-family ADR. That session checks
rule 3 of `adr-rules.md` — whether template text outside `ask` and document artifacts are one
decision or two — and separates ADR matter from component work: a grouped-table renderer is
writable today as one more function; the ADR question is the mechanism that stops the next format
from being the seventh syntax.
