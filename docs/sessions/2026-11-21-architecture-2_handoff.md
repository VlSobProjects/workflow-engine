# Session 2026-11-21-architecture-2

## Type
architecture

## Goal
Put the public showcase ahead of roadmap step 14: capture the idea as a note, open the human-readable
run report as a Draft ADR in the core, and add the showcase steps to the phase 2 roadmap.

## Completion criteria
- A note in `docs/architecture/notes/` records the showcase idea — a demonstration run on demand in CI
  that publishes a human-readable report of the run — with its alternatives and their cost, and links
  the `storage-read-contract` note.
- A Draft ADR states the run report as an engine command producing one self-contained HTML document
  from the read surfaces, with at least two alternatives, the trade-offs, the cost and its open
  questions.
- `roadmap.md` carries the showcase steps ahead of step 14 — the report, the CI demonstration, and the
  authoring skill as a measurement of the floor, conditional on its own architecture session — with
  the reason for departing from the order set by `2026-08-25-architecture-2`.
- The registries of notes and ADRs carry the new rows.

## Scope boundaries
- No code, no workflow file under `.github/`, no template.
- The ADR stays Draft; its open questions are not settled here.
- The place of a Skill in the documentation map and the authoring skill itself are left to their own
  architecture session.
- A component catalogue (`help` rendered as HTML) is not opened.

## Status
`completed`

## Result
- Note `2026-11-21-run-report-and-public-showcase` (committed separately at the start): the need, the
  two pages hidden in the original idea, five placements with their cost, the CI demonstration and
  three options for authoring by an agent; registered under the current phase.
- Draft ADR 022 `adr-022-human-readable-run-report.md` and its registry row: a `report` command
  writing one self-contained HTML document of a session from the read surfaces and the `Storage`
  contract, six alternatives, seven open questions.
- `folder-inventory-to-csv` and `load-test-triage` list ADR 022, in their headers and in the scenario
  registry (rule 11).
- The `storage-read-contract` note and the showcase note name ADR 022 in `Affected`, in the notes and
  in the registry (rule 12).
- `roadmap.md`: steps 16 to 18 ahead of step 14, with the reason in the order paragraph.

## Decisions
1. **The report lives in the engine, as a command.** The need is the engine's own: its promise of an
   explained run reaches a human only through a program that composes four read commands, and the
   definition has no read surface. Alternatives: a CI script over the files of `JsonStorage`
   (cheapest, bound to one backend, no report for an operator), a CI script over the `--json` read
   commands (backend-neutral, still no report for an operator), `--html` on each read command (no
   single account of the run), a workflow over the ADR 020 renderer (would push iteration into
   templates), Markdown (viewer-dependent, poor for nested configuration). Cost: one ADR, one or two
   implementation sessions, a template kept in step with the state and record shapes.
2. **The report reads through the read surfaces and the `Storage` contract only**, so it holds on the
   database backends the `storage-read-contract` note expects.
3. **The run report and a component catalogue are two things**; only the report is opened.
4. **A static document is not a user interface** in the sense of the purpose's boundary: no server,
   no interaction, no live view. A live or interactive view stays closed off.
5. **The public showcase goes ahead of step 14**, as the owner's priority once the repository is
   public. Step 14 needs the load rig and a live system under test; the showcase gives a reader a
   result now. The alternative, keeping the order, leaves a public repository with nothing to show
   but command output for the length of step 14.
6. **Authoring by an agent is the floor, conditional.** Against `2026-08-25-architecture-2`, which
   moved authoring to phase 3, step 18 is the floor measurement — an agent writes a definition from
   the documentation and proves it by a run — not the phase 3 exit, and it waits for its own
   architecture session. The full `workflow-authoring` cycle now (ADR 019, G11) was rejected as
   moving phase 3 into phase 2.

## Open questions
- The seven open questions of ADR 022.
- Whether step 18 stays in phase 2, and where a Skill lives in the documentation map.

## Next steps
1. An architecture session settles the open questions of ADR 022 and moves it to Implementing.
2. The implementation on `feature/adr_022-human-readable-run-report`, with the walkthrough of
   `folder-inventory-to-csv` showing the report, `README.md` and the overview; run
   `gh workflow run ci.yml --ref <branch>` there to confirm the manual run (next step 3 of
   `2026-11-21-maintenance-2`).
3. The maintenance session of step 17: the CI demonstration publishing the reports on GitHub Pages.
4. The architecture session of step 18.

## References
- Branch: `development`
- ADR 022 (Draft)
- Notes: `2026-11-21-run-report-and-public-showcase`, `2026-11-21-storage-read-contract`
- Changed: `docs/adr/README.md`, `docs/architecture/roadmap.md`, `docs/architecture/notes/README.md`,
  `docs/architecture/scenarios/README.md`, `docs/architecture/scenarios/load-test-triage.md`,
  `examples/folder-inventory-to-csv.md`
