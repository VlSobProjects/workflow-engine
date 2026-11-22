# Session 2026-11-21-architecture-3

## Type
architecture

## Goal
Settle the seven open questions of ADR 022 and move it from Draft to Implementing.

## Completion criteria
- Each of the seven open questions of ADR 022 is decided with at least two alternatives, the
  trade-offs and the cost, and the decision is written into the ADR's `Decision` section; the open
  questions list is removed from the implementation notes.
- The ADR change log records the amendment.
- ADR 022 is `Implementing` with its active branch `feature/adr_022-human-readable-run-report`, in the
  ADR file and in the registry, and the branch exists, created from `development`.
- Roadmap step 16 states the new state of the step.
- Every note the decisions touch has its `Affected` link or `Status` updated (ADR rule 12).

## Scope boundaries
- No code, no template, no CI workflow.
- Step 17 (the CI demonstration) and step 18 (authoring by an agent skill) are not discussed.
- The read contract of the `storage-read-contract` note is not decided; the report only reads through
  the `Storage` contract.

## Status
`completed`

## Result
- ADR 022: the seven open questions decided and written into §1, §3, §4 and §5; §4 rewritten to a fact
  model the engine builds and an embedded viewer that renders it; two alternatives added; the
  Context, Consequences, implementation notes and change log updated; status `Implementing`, active
  branch `feature/adr_022-human-readable-run-report`, in the file and in the registry.
- The `storage-read-contract` note records the owner's plan of a web interface as a decision of its
  own that revisits the boundary of `purpose.md`, and names `purpose.md` in `Affected`, in the note
  and in the notes registry.
- Roadmap step 16 states the move to Implementing and the three planned implementation sessions.

## Decisions
All recorded in ADR 022.
1. **A node in two views**: the configuration as written, and the effective transitions as built
   with their origin, because a record names a guard and not its transition; a failed build degrades
   to the written view and states the error.
2. **Values by default**, cut at a fixed length with a pointer to `show-parameter`, `--no-values` to
   leave them out; artifacts by logical name and relative path, never content.
3. **A paused session is reported from the definition**: the answer declaration, the error catalogue,
   the presentation as template text and the `resume` form; no presentation code runs.
4. **The graph is listed, not drawn**; a drawn graph is a later decision.
5. **The template is not replaceable**, and **HTML is the only format**.
6. **The document goes into the session directory** as `report.html`, `--output` elsewhere; it is not
   an artifact, which would change the state from a read command.
7. **A fact model and an embedded viewer** (§4): the engine builds the facts in Python through the
   `Storage` contract and embeds them as JSON; an inline script renders the interactive report and
   reaches neither the network nor the session. Alternatives: a script reading the session's files
   (rejected — a page opened from a disk cannot read files, it binds the report to `JsonStorage`,
   repeats the engine's semantics in JavaScript and cannot read a database backend) and a document
   rendered wholly in Python (not chosen — the showcase and the later interface need interaction).
   Cost: the viewer is outside `pytest` and `ruff`, checked by hand; no report with scripts disabled.
8. **The web interface is a decision of its own**, revisiting the boundary of `purpose.md`; ADR 022
   neither takes nor prepares it beyond keeping facts apart from their presentation.
9. **Design before code**: the first implementation session is a mockup of the viewer over a real
   model of `folder-inventory-to-csv`, agreed with the owner and kept outside the repository.

## Open questions
- Whether the viewer later earns automated tests, which need a JavaScript toolchain and an approved
  dependency.
- The web interface and the boundary of `purpose.md`, left to their own architecture session.

## Next steps
1. Implementation session 1 on `feature/adr_022-human-readable-run-report`: the design mockup of the
   viewer over a real model of `folder-inventory-to-csv` — completed with its loop, paused, failed —
   published as a private page for the owner's review.
2. Implementation session 2: the model builder, the `report` command and the viewer from the agreed
   mockup, with tests over the model and the data block.
3. Implementation session 3: `README.md`, the overview and the `folder-inventory-to-csv` walkthrough
   showing the report; run `gh workflow run ci.yml --ref <branch>` there (next step 3 of
   `2026-11-21-maintenance-2`); merge and freeze.
4. Step 17, the CI demonstration, then the architecture session of step 18.

## References
- Branch: `development`; created at the end: `feature/adr_022-human-readable-run-report`
- ADR 022 (Implementing)
- Note: `2026-11-21-storage-read-contract`
- Changed: `docs/adr/adr-022-human-readable-run-report.md`, `docs/adr/README.md`,
  `docs/architecture/roadmap.md`, `docs/architecture/notes/2026-11-21-storage-read-contract.md`,
  `docs/architecture/notes/README.md`, `docs/sessions/README.md`
