# Session 2026-11-22-implementation-1

## Type
implementation

## Goal
Design the viewer of ADR 022 as a mockup over real session facts and agree it with the owner before
any code is written.

## Completion criteria
- Four real sessions exist outside the repository, produced by the engine as it is: a completed run
  of `folder-inventory-to-csv` over a prepared tree with nested folders, a failed run of it (an empty
  tree, `pretty_table_no_data`), a run of it paused on the session budget inside its loop, and a run
  of `approve-and-copy` paused at its question.
- A draft fact model of each session is written by hand from the read commands' `--json` answers and
  the definition, in the shape §3 and §4 of ADR 022 describe, as the proposal for the model builder.
- A mockup of the viewer renders those models: the session header and its ending, the path with
  collapsible loops and the visits of one node highlighted, both views of a node, the graph as a
  list, the parameters with cut values, the artifacts, the paused block; light and dark themes, a
  narrow screen, printing, keyboard use and a stable anchor for every node and visit.
- The mockup is published as a private page and the owner's corrections are applied or recorded.
- The mockup and the draft models stay outside the repository; the session note records the agreed
  design decisions and the model shape.

## Scope boundaries
- No engine code, no `report` command, no tests, no package data: that is implementation session 2.
- No change to `README.md`, the overview or the walkthrough: that is implementation session 3.
- ADR 022 is not amended; a design finding that contradicts it is raised, not written into the ADR.

## Status
`completed`

## Result
- Four real sessions produced by the engine as it is, outside the repository: a completed run of
  `folder-inventory-to-csv` over a tree with nested folders (33 visits, a loop of 8 passes), a failed
  run of it over an empty tree (`pretty_table_no_data`), a run of it paused on a session budget of
  14 visits inside the loop, and a run of `approve-and-copy` paused at its question.
- A draft fact model of each, built by a throwaway script from the read commands' `--json` answers
  and the session's definition, with the effective transitions taken from the engine's own node
  build and the values from its single rendering rule.
- The viewer mockup over the four models, published as a private page and agreed with the owner in
  its third version; it and the models stay outside the repository.
- ADR 022 amended from the mockup (see Decisions); it stays `Implementing`.
- The scope boundary that kept ADR 022 unamended was lifted by the owner once the drawn graph and the
  `~` replacement were decided: both contradicted the ADR as written, and the amendment lands with
  this note instead of a session of its own.

## Decisions
All recorded in ADR 022.
1. **The graph is drawn as well as listed**, laid out by the viewer from the effective transitions,
   with no coordinate in the model. Alternatives: the layout in Python with coordinates in the model
   (not chosen — presentation in the fact model) and an embedded layout library (not chosen — a
   dependency in every document). Cost: viewer code outside `pytest`, and crossings on a large graph.
2. **The design**: header with the ending in one sentence and the pending block above five tabs —
   Graph first, then Path, Parameters, Artifacts, Journal — a node in a dialog, every tab, visit,
   node and parameter an anchor, every tab printed in turn; system fonts only.
3. **The home directory in the rendered values is replaced by `~`**, stated in the document; other
   paths stay, `--no-values` covers them. Alternatives: values as they are (leaks a user name), the
   session directory replaced (misses the inputs), a `--redact-path` flag (no consumer asks for it).
4. **The model carries the origin of the transition each visit took and marks workflow inputs**;
   the written view of a node is copied before the build, which writes into its configuration.
5. **The viewer is tested in a browser by an opt-in Playwright suite in Python** against the reports
   of several shipped workflows, outside the default `uv run pytest`, in its own dependency group and
   CI job; the dependency approved by the owner. Alternatives: the browser tests in the default run, a
   JavaScript runner without a browser, checking by hand only.

## Open questions
- Nested loops are not grouped by the mockup's path; only the first loop folds into passes.
- No shipped example has `validators`, so the `validators[i]` origin is not exercised by the mockup.
- `list-parameters` attributes a workflow input to the first node of the run; the report marks it,
  the read command is not changed here.

## Next steps
1. Implementation session 2: the model builder, the `report` command and the viewer from the agreed
   mockup, with the `~` replacement, tests over the model and the data block.
2. The Playwright suite, its marker, its dependency group and its CI job, once the viewer is in the
   package: in session 2 or a session of its own right after it.
3. Implementation session 3: `README.md`, the overview and the walkthrough; the CI run on the branch;
   merge and freeze.

## References
- Branch: `feature/adr_022-human-readable-run-report`
- ADR 022 (Implementing)
- Changed: `docs/adr/adr-022-human-readable-run-report.md`
