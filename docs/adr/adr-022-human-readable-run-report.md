# ADR 022: A human-readable report of one session

## Status
Implementing

## Active branch
`feature/adr_022-human-readable-run-report`

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
  A script inside the document that presents its own data and reaches neither the network nor the
  session stays on that side too. The owner plans a web interface to the engine later and wants the
  report to grow into it; that plan crosses the boundary and is a decision of its own, recorded in the
  `storage-read-contract` note, which this ADR neither takes nor prepares beyond keeping the facts
  apart from their presentation.
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
A new command, `workflow-engine report --session-id <session_id>`, writes one HTML document
describing that session; the session is named by the option every other session command takes. It
reads the session and never changes it, under the same session lock discipline as the other read
commands: it takes no lock, and it is an info command that answers `0` wherever the workflow stands.
It answers in the ADR 007 `CommandResult`, with `--json` as everywhere, naming the path of the
written document.

The document is written by default into the session's own directory as `report.html`, so the account
of a session lives and is removed with the session; `--output <file>` writes it elsewhere instead, as
a publishing step does. A second report of the same session replaces the first. Writing the document
is not a change of the session: the state, the journal and the records are untouched. The report is
deliberately not an artifact of the session (ADR 011): registering one would change the state from a
read command.

### 2. The report is assembled from the read surfaces, never from a backend's files
Its facts come from what the engine already serves to its read commands — the state view, the
journal, the record stream — and the definition through the `Storage` contract (`load_workflow`),
never by opening files of `JsonStorage`. The report is therefore the first in-core reader of the
definition the session runs; how that read becomes a published surface is left to the
`storage-read-contract` note, and this ADR takes no position on it beyond reading through the
contract.

### 3. What the document shows
- The session: its identifier, the workflow, the status, and how the run ended — completed, failed
  under a code, or paused: at the pending question, or on the session budget or the hard cap with
  the visits counted, each pause with the commands that continue it.
- The path: the visited nodes in order, from the records, with visit and attempt ordinals, status,
  error code, the guards evaluated and the transition taken.
- The nodes, each opened from the graph and from the path, in two views side by side. The configuration as the session's definition holds it, which
  is what the author recognises; and the effective transitions as the node is built, `validators`
  expanded into leading failure transitions (ADR 002), each marked with its origin
  (`validators[i]` or `transitions[i]`). The second view is needed because a node record names a guard
  but not the transition it belongs to. The visited nodes link to their visits and back. When the
  nodes cannot be built — a component module that no longer loads — the report is still written: the
  transitions are shown as written and the build error is stated in the document.
- The graph, drawn and listed. The drawing shows every node with its action, its visit count and
  whether it failed or is where the run stands, and every effective transition as an arrow labelled
  with its guard and the number of visits that took it; a transition back into a loop and a node
  that returns to itself are drawn as such, and an end or a failure target is a terminal of its own.
  The list states the same graph as text, every target a link to its node. The layout is
  presentation: the viewer computes it from the effective transitions in the model, and the model
  carries no coordinate.
- The parameters: names, codecs, the node that wrote each or that it is a workflow input, and the values, shown by default. A value
  is rendered by the single rendering rule of ADR 016 and cut at a fixed length; a cut value says that
  it was cut, its full length, and that `show-parameter` reads it whole. `--no-values` writes the
  report without values. The state holds no secret — a provider block names its credential, never
  holds it (ADR 014) — so the switch serves size and publication, not secrecy. A value does carry the
  paths the session was given, and a path under a home directory names the person who ran it: in the
  rendered values the home directory of the machine writing the report is replaced by `~`, and the
  document states that it was. A path outside it stays as the session names it; `--no-values` is the
  answer for those.
- The artifacts: logical names and paths relative to the session directory, never their content, so
  the document carries no path of the machine that ran the session beyond what the session itself
  names.
- A paused session: the pending node, its answer declaration and error catalogue, its presentation
  fields twice — as the template text the definition holds, and as they were presented, resolved by
  the template rule of ADR 016 against the state — and the form of the
  `resume <session_id> --answer ...` command that continues it. The paused node has not run since it
  presented its question, so the resolved text is the text the answerer was shown; the viewer shows
  it first and the template text on a switch. The resolved text is a rendering of values: the home
  directory is replaced by `~` in it as in the values, `--no-values` leaves it out, and a reference
  that no longer resolves leaves the question as written with the reason stated. The question is not
  re-rendered as a published block: the fields are resolved one by one into the model, and the
  published question shape stays the subject of Draft ADR 019.

### 4. One self-contained file: a fact model the engine builds, a viewer embedded beside it
The engine builds a model of the facts of the session — everything §3 shows, with the effective
transitions already built and the values already rendered — through the `Storage` contract, and
embeds it in the document as a JSON data block. An inline script, the viewer, renders the interactive
report from that block: the drawn graph, the path with collapsible loops, the visits of one node
highlighted, filters, links between visits, nodes and parameters. All the semantics of the engine — the build of a node,
the rendering of a value through its codec — stays in Python, in one place; the viewer only presents
what the model states and never computes an engine fact.

The document embeds its styles, its viewer and its data and carries no script, font or image from
outside, so it opens from a disk or a static host with no network. The viewer reaches neither the
network nor the session: it reads the block it was shipped with and nothing else. Without a script
the document says that the report needs JavaScript; no second, static rendering is produced.

The model is internal: it is the interface between the engine's Python and the engine's own viewer,
both shipped in one package, and it carries a `schema_version` so a document states which model it
holds. It is not a published contract (see below on the template). The document is produced with the
standard library, and the viewer and the styles ship as package data of the engine. The engine takes
no new dependency; the viewer's tests take one, in a group of their own (see Consequences).

The template — the shell, the styles and the viewer — is the engine's and is not replaceable: no
configuration key and no flag names another. A replaceable template would publish the model handed to
it as a contract. A program that wants a report of its own
design composes the read commands with `--json`. HTML is the only format; the text renderings of the
read commands and their `--json` answers already serve a terminal and a program.

### 5. Out of scope
No catalogue of components, no view across sessions, no live refresh, no action on the session from
the document, no replaceable template, no second format. Each is a separate decision
if a consumer asks for it.

## Alternatives considered

- **A script outside the engine reading the files of `JsonStorage`.** Cheapest. Bound to one
  backend's layout, which the `storage-read-contract` note keeps out of the contract, and no report
  for an operator outside the place the script lives. Rejected: it serves the demonstration and not
  the need.
- **A viewer in the document reading the session's files beside it.** The script loads the JSON files
  of the session at open time and renders them, so the report is always current and is already shaped
  like an interface. Rejected: a browser refuses to read local files into a page opened from a disk,
  so the report needs a server to open; it binds the report to the files of `JsonStorage`, which are
  an internal serialization and not the definition as written; it repeats the engine's semantics —
  the expansion of `validators`, the rendering of a value through its codec — in a second language;
  and a browser cannot read a database backend at all, so it does not lead to an interface either,
  which needs an API whatever the backend.
- **The document rendered entirely in Python, with no script or only a small one.** Every fact the
  reader sees is in the HTML a test reads, so `pytest` checks what is shown. Not chosen: the owner
  wants the report as the engine's showcase and the seed of a later interface, and interaction on a
  long path — filtering, highlighting the visits of one node — needs a script; a viewer over a model
  serves both, at the cost of a viewer that the tests do not see.
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
  sections, a drawn graph needs an embedded image, and it carries no viewer at all.
- **The graph laid out by the engine, its coordinates in the model.** The layout would be in Python and
  under `pytest`. Not chosen: a layout is presentation, the model keeps facts apart from it, and every
  change of the drawing would become a change of the model's shape.
- **The graph laid out by an embedded library** (a layered-layout library, or a diagram language
  rendered in the page). A layout of better quality for large graphs at no code of the engine's own.
  Not chosen: a new dependency carried inside every document, at up to a megabyte for a diagram
  language; the viewer's own layered layout serves the graphs of the shipped examples, and a graph
  large enough to need more is a reason to revisit this.
- **Do nothing; the text renderings of the read commands suffice.** Rejected: they serve a terminal
  user who already knows which command answers which question, not a reader of the run.

## Consequences
- The CLI contract gains a command (ADR 007), documented in `README.md` and the overview; the help
  surfaces list it.
- The engine ships a fact model and a viewer it must keep in step with the state, the record shape
  and the definition format: every change to those becomes a change to the model, caught by tests
  that build the model of the evidence example, and a change of the model's shape raises its
  `schema_version`.
- The viewer is JavaScript, which neither `pytest` nor `ruff` checks. The tests cover the model in
  full and check that the document carries a well-formed data block and the viewer. The viewer itself
  is checked in a real browser by an opt-in suite of Playwright tests written in Python, run against
  the reports of several shipped workflows: completed with a loop, failed, paused on the budget,
  paused at a question. The suite stays outside the default `uv run pytest`, behind a marker of its
  own and a dependency group of its own — `pytest-playwright` and the browser it downloads, approved
  by the owner for this purpose and never a dependency of the engine at run time — and runs in a CI
  job of its own, so a fresh clone and the test matrix on three systems need no browser. Rejected
  alternatives: the browser tests in the default run (every clone and every system would need a
  browser), a JavaScript test runner without a browser (a toolchain of its own that sees neither
  layout nor behaviour), and checking by hand only (no regression of the showcase would be caught).
- A reader with scripts disabled sees no report, only the statement that it needs JavaScript.
- A later web interface can reuse the viewer with the model served by an API instead of the embedded
  block; nothing in this ADR promises it.
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
- Building the effective transitions needs the components loaded, as `run` does; the build is used
  only to read the transitions, never to run a node.
- The length at which a value is cut is a constant of the report, chosen in the implementation and
  stated in the help of the command.
- The data block is JSON inside `<script type="application/json">`; the sequences that would close or
  comment out the element (`</`, `<!--`) are escaped when the block is written.
- The report is the engine's showcase, so its design is worked out before the code. The work runs in
  three sessions on the feature branch: first, a design mockup of the viewer over a real model of
  `folder-inventory-to-csv` — a completed run with its loop, plus a paused and a failed session —
  agreed with the owner and kept outside the repository, where it lands only as the shipped viewer;
  second, the model builder, the command and the viewer from the agreed mockup; third, `README.md`,
  the overview and the walkthrough.
- The design covers a light and a dark theme, a narrow screen, printing, keyboard use, and a stable
  anchor for every node and every visit, so a link to one point of a run can be shared.
- The design agreed in session `2026-11-22-implementation-1`: the session header with its ending in
  one sentence and the pending block above five tabs — Graph (first, the drawing with the list as a
  second view), Path, Parameters, Artifacts, Journal — each tab and each visit, node and parameter an
  anchor; a node opens in a dialog from the graph, the path and the list; printing lays every tab
  and every node out in turn.
- What the mockup found the model needs beyond the read commands: the origin of the effective
  transition each visit took, decided in Python, because a record names a guard and not its
  transition; and a mark on a parameter that is a workflow input, which `list-parameters` attributes
  to the first node of the run. Building a node writes into the configuration it is handed, so the
  written view is copied before the build.
- The Playwright suite is written once the viewer is in the package, in implementation session 2 or
  a session of its own right after it; its CI job runs on one system.

## Change log
- 2026-11-21: opened as Draft in session `2026-11-21-architecture-2`.
- 2026-11-21: the seven open questions settled in session `2026-11-21-architecture-3`: both views of a
  node with the build failure degrading to the written one, values by default with a cut and
  `--no-values`, artifacts by relative path, a paused session reported from the definition, the graph
  listed and not drawn, the template not replaceable, the document written into the session directory
  with `--output`, HTML the only format. §4 rewritten in the same session: the engine embeds a fact
  model and an inline viewer renders it, replacing the document without a script; the owner's plan of
  a web interface recorded in the Context as a separate decision; moved to Implementing on
  `feature/adr_022-human-readable-run-report`.
- 2026-11-22: amended in session `2026-11-22-implementation-1` from the design mockup: the graph is
  drawn as well as listed, laid out by the viewer with no coordinate in the model, and the drawn graph
  leaves the out-of-scope list; two alternatives on where the layout lives added; the home directory
  in the rendered values replaced by `~`, stated in the document; a workflow input shown as such;
  the agreed design and the model's findings recorded in the implementation notes; the viewer tested
  in a browser by an opt-in Playwright suite in its own dependency group and CI job.
- 2026-11-22: amended in session `2026-11-22-implementation-2` at the owner's request after reading
  the report of a paused question: the presentation fields are carried as presented as well as
  written, resolved in Python by the ADR 016 rule and shown first, the template text on a switch.
  Alternatives: the template text alone, as decided before (the reader matches references to values
  by hand), and the references resolved by the viewer (a second implementation of the template rule
  in JavaScript, and `output.` and `artifact.` references the model does not carry).
- 2026-11-24: amended in session `2026-11-24-implementation-2` to the result as built: §1 names the
  session by `--session-id`, as every other session command does, instead of a positional argument,
  and states that the command takes no lock and is an info command; §3 states the pause on the
  budget and on the hard cap beside the pause at a question. The work took four sessions on the
  branch rather than three: the Playwright suite had a session of its own,
  `2026-11-24-implementation-1`.
