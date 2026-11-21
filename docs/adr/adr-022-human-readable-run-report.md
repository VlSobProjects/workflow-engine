# ADR 022: A human-readable report of one session

## Status
Draft

## Active branch
—

## Context
The purpose promises a run whose path is "determined by the data and explained by the journal". The
engine keeps everything that explanation needs — the state, the journal, the node records (ADR 021),
the definition the session runs — and serves it through bounded read commands (ADR 018, ADR 021):
`show-state`, `list-parameters`, `show-parameter`, `show-journal`, `show-records`. Each answers one
question, as text for a terminal or as JSON for a program. None gives a person one account of the
run: the graph, the path taken through it, each visited node with its configuration, the guards that
chose each transition, the parameters with their codecs, the artifacts, and how the run ended or why
it stopped. A human who wants to understand a session runs four or five commands and joins their
answers by hand, and the definition the session runs has no read surface at all.

The need became visible when the repository was opened for reading: a public demonstration of a run
has nothing to show but command output. The demonstration is the first consumer, not the reason —
the reason is that the engine's own promise of an explained run reaches a human only through a
program that composes the read commands.

Constraints:
- The purpose excludes a user interface. A document written on demand, read offline, with no server
  and no interaction with the session, is a rendering of persisted facts — of the same kind as the
  `file_scan_report` of ADR 020 — not an interface; the decision must stay on that side of the line.
- The note `2026-11-21-storage-read-contract` expects database backends. A report bound to the files
  of `JsonStorage` would break on the first of them.
- Records and the journal carry names, never values (ADR 013 §9, ADR 021 §1); values live in the
  state, behind the codec envelope.
- Dependencies are kept minimal; the standard library is preferred.

## Consumer
The party that acts on this decision is a human who reads a session after the fact or at a pause —
the operator, or a reader shown the run — holding a browser and the document, and not the CLI. The
freeze-gate evidence is class 4: `folder-inventory-to-csv` (`examples/folder-inventory-to-csv.md`),
whose queue-driven walk visits its loop nodes once per tree entry, so the report must show a path
with repeated visits, the guards that ended the loop and the two deliverables; the walkthrough shows
the report of a run over a prepared tree, and it and the scenario registry list this ADR in the same
session. The phase consumer is `load-test-triage` (`docs/architecture/scenarios/load-test-triage.md`),
whose human receives the verdict or the handover and must be able to read why the run took its path.

## Decision

### 1. One command writes one document for one session
A new command, `workflow-engine report <session_id>`, writes one HTML document describing that
session. It reads the session and never changes it, under the same session lock discipline as the
other read commands. It answers in the ADR 007 `CommandResult`, with `--json` as everywhere, naming
the path of the written document.

### 2. The report is assembled from the read surfaces, never from a backend's files
Its facts come from what the engine already serves to its read commands — the state view, the
journal, the record stream — and the definition through the `Storage` contract (`load_workflow`),
never by opening files of `JsonStorage`. The report is therefore the first in-core reader of the
definition the session runs; how that read becomes a published surface is left to the
`storage-read-contract` note, and this ADR takes no position on it beyond reading through the
contract.

### 3. What the document shows
- The session: its identifier, the workflow, the status, and how the run ended — completed, failed
  under a code, or paused with the pending question.
- The path: the visited nodes in order, from the records, with visit and attempt ordinals, status,
  error code, the guards evaluated and the transition taken.
- The nodes: the configuration of each node of the definition, the visited ones linked to their
  visits.
- The parameters and artifacts: names, codecs, the node that wrote each, and the values where the
  state holds them, rendered through their codecs.

### 4. One self-contained file, standard library only
The document embeds its styles and carries no script, font or image from outside, so it opens from a
disk or a static host with no network. It is produced with the standard library — escaping through
`html.escape` — and its template ships as package data of the engine. No new dependency.

### 5. Out of scope
No catalogue of components, no view across sessions, no live refresh, no action on the session from
the document. Each is a separate decision if a consumer asks for it.

## Alternatives considered

- **A script outside the engine reading the files of `JsonStorage`.** Cheapest. Bound to one
  backend's layout, which the `storage-read-contract` note keeps out of the contract, and no report
  for an operator outside the place the script lives. Rejected: it serves the demonstration and not
  the need.
- **A script outside the engine composing the read commands with `--json`.** Backend-neutral and a
  real test of the published surfaces. Rejected as the decision because an operator still gets no
  report without carrying the script, and the definition has no read command to compose; it remains
  what a program does that wants a report of its own design.
- **A third presenter, `--html` on each read command.** No new command. Rejected: each command renders
  its own fragment, and the need is one account of the run in one place.
- **The report as a workflow using the ADR 020 template renderer.** Dogfooding. Rejected: ADR 020
  decided that templates substitute and never iterate, and a path of visited nodes cannot be written
  without iteration; the report would push iteration into the renderer.
- **Markdown instead of HTML.** Text, diffable, rendered by code hosts. Not chosen: its rendering
  depends on the viewer, nested node configuration and long loops read poorly without collapsible
  sections, and a drawn graph needs an embedded image. Kept open as question 7 should HTML prove the
  wrong medium.
- **Do nothing; the text renderings of the read commands suffice.** Rejected: they serve a terminal
  user who already knows which command answers which question, not a reader of the run.

## Consequences
- The CLI contract gains a command (ADR 007), documented in `README.md` and the overview; the help
  surfaces list it.
- The engine ships an HTML template it must keep in step with the state, the record shape and the
  definition format: every change to those becomes a change to the report, caught by tests that
  render the evidence example.
- The report is the first in-core reader of the definition the session runs; a database backend must
  serve it through the `Storage` contract as it does today.
- The public demonstration — a CI run on demand publishing the document — becomes a thin maintenance
  task over this command rather than a generator of its own.
- Closed off for now: an interactive or live view, which would cross the purpose's boundary on user
  interfaces and needs its own decision.

## Related ADRs
- Depends on ADR 007 (CLI contract), ADR 018 (session read surfaces), ADR 021 (the node-record
  channel).
- Constrained by ADR 013 §9 and ADR 021 §1 (names, never values, in the trails), ADR 003 (the
  medium-neutral storage contract), ADR 008 (paths in POSIX form), ADR 020 (templates substitute and
  never iterate), ADR 009 (help surfaces).
- Note: `2026-11-21-run-report-and-public-showcase` (origin), `2026-11-21-storage-read-contract`.

## Implementation notes
Open questions to settle before Implementing:
1. The node as written in the definition, or as built — `validators` expanded into leading failure
   transitions (ADR 002) — or both.
2. Whether parameter values appear by default, and how a large or sensitive value is bounded — the
   ADR 018 bounds, a cut-off, or a switch that leaves values out.
3. How a paused session is reported: the pending question, its answer declaration and the command
   that resumes it.
4. Whether the graph is drawn — an inline SVG with a layout computed by the engine without a
   dependency — or listed as nodes and edges.
5. Whether an operator may replace the template, and if so how it is named in configuration.
6. Where the document is written: a path the operator names, the session directory, or an artifact of
   the session (ADR 011), and the command's name accordingly.
7. Whether HTML stays the only format or the text rendering of the same report is offered beside it.

## Change log
- 2026-11-21: opened as Draft in session `2026-11-21-architecture-2`.
