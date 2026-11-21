# A human-readable report of a run, and the public showcase built on it

- **Date:** 2026-11-21
- **Trigger:** discussion at the start of session `2026-11-21-architecture-2`, after the repository was
  opened for reading (`2026-11-21-architecture-1`, `2026-11-21-documentation-1`) and the CI pipeline
  gained an on-demand run (`2026-11-21-maintenance-2`). The owner proposed a demonstration started by
  hand in CI that runs a workflow and publishes an HTML page describing the run: its nodes, results,
  parameters, the configuration of the nodes and the codecs.
- **Status:** `open`
- **Affected:** ADR 022 (the run report, opened from this note as Draft), ADR 007 (CLI contract — a new command), ADR 018 (session read surfaces), ADR 021 (the
  node-record channel), ADR 020 (template rendering — why it is not the vehicle), ADR 009 (help
  surfaces — the component catalogue left out), the notes `2026-11-21-storage-read-contract`,
  `2026-11-21-published-contract-and-consumer-requests`, `2026-08-21-agent-instruction-and-skill`,
  `docs/architecture/roadmap.md` (the order of phase 2)

## The idea

Two needs met by one piece of work.

1. **The engine has no human-readable account of a run.** The read commands give the state, the
   parameters, the journal and the node records one at a time, as text or as JSON. Nothing gives a
   person one document that tells what the run did: the graph, the path taken, each visited node with
   its configuration, the guards that decided the transitions, the parameters with their codecs, and
   how the run ended. An operator who wants to understand a finished or paused session reads four
   commands and joins them in their head.
2. **A public showcase.** The repository is readable in public. A page produced by a real run, on
   demand, in CI, shows a reader faster than the README that the engine runs and that the journal
   explains the chosen path.

The first need is the reason the report belongs to the engine; the second is its first consumer.

## Two pages hidden in the original idea

- **The run report** — dynamic: the facts of one session.
- **The component catalogue** — static: actions, guards, functions and codecs with their
  configuration and examples. It needs no run; it is a rendering of the help contract (ADR 009).

Built by one generator they couple a run to the component inventory and grow together. Only the run
report is taken further here; the catalogue, if wanted, is a separate `help` rendering.

## Where the report is produced

| Option | What | Cost | Trade-off |
| --- | --- | --- | --- |
| A. A script outside the engine reads the files of `JsonStorage` | `state.json`, `records.jsonl`, `workflow.json` | lowest | bound to one backend's files, which the `storage-read-contract` note keeps out of the contract; breaks on the first database backend; no report for an operator outside CI |
| B. A script outside the engine calls the read commands with `--json` | the published read surfaces | low | backend-neutral, a first external reader of the contract; still no report for an operator, and the definition has no read surface today |
| C. An engine command that writes one self-contained HTML document | `workflow-engine report <session>` | an ADR, one or two implementation sessions, documentation | a new command in the CLI contract; the report available to every operator; built on the same read surfaces as the commands |
| D. A third presenter, `--html` on each read command | beside `render_text` and `render_json` | medium | no new command, but each command renders its own fragment and no single account of the run exists, which is the need |
| E. The report is itself a workflow using the ADR 020 template renderer | dogfooding | medium | ADR 020 decided that templates substitute and never iterate; a list of visited nodes cannot be written without iteration, so the showcase would drive a feature into the renderer |

The discussion chose **C**, under two constraints for the ADR:

- **Data source.** The report is assembled from the facts the read surfaces serve, not from the files
  of `JsonStorage`, so it holds on any backend. It is the first in-core reader that needs the
  definition the session runs, which has no read surface today (open question 1 of the
  `storage-read-contract` note).
- **Scope.** One session, one document. No catalogue, no cross-session view, no live refresh.

## The showcase around it

- **The CI demonstration.** A workflow started by `workflow_dispatch` runs one or two shipped examples
  that need no model server — `folder-inventory-to-csv`, `flatten-copy-tree`, `approve-and-copy` with
  a scripted `resume --answer` to show a pause — or a variant with the `fake` adapter, stated on the
  page as a canned model answer. It runs `report` and publishes the document on GitHub Pages. A
  maintenance session, after the report exists. Pages are public: the page must carry no path or name
  of the runner beyond what the report already prints.
- **Authoring by an agent.** The owner wants workflow assembly shown before phase 2 closes, through an
  agent skill. `2026-08-25-architecture-2` moved authoring to phase 3, whose exit is the assisted
  `workflow-authoring` cycle, and the roadmap calls a definition written directly from the
  documentation the floor, not that exit. Alternatives:
  - *Keep it in phase 3* — no cost, a showcase without authoring.
  - *A skill as the floor in phase 2* — the agent writes a definition from the documentation and
    proves it by a run; one or two sessions plus the decision on the place of a Skill in the
    documentation map, which `2026-08-21-agent-instruction-and-skill` records the map does not admit.
    It is also the floor measurement phase 3 compares against.
  - *The full `workflow-authoring` cycle now* — ADR 019 and the authoring surfaces (G11); it moves
    phase 3 into phase 2.

  The discussion leans to the floor, decided in its own architecture session. If it is built before
  roadmap step 15, the hand-build of step 15 must not use it, or the documentation-sufficiency claim
  of phase 2 loses its evidence.

## Open questions

1. What the report shows of a node's configuration: the node as written in the definition, or as built
   (validators expanded into leading failure transitions).
2. Whether parameter values appear in the report, given that records and the journal carry names,
   never values; values come only from the state through the codec envelope.
3. How a paused session is reported: the pending question, the answer declaration, the resume command.
4. Whether the graph is drawn (inline SVG laid out by the engine) or listed; a drawing needs a layout
   without a dependency.
5. Where the HTML template lives — package data of the engine — and whether an operator may replace it.
6. Whether the report is written as an artifact of the session or only to a path the operator names.
