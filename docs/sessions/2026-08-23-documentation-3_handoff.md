# Session note: 2026-08-23 documentation 3

## Type
`documentation`

## Goal
Give the three shipped examples their class 4 scenario headers in `examples/` and one registry row
each in `docs/architecture/scenarios/`, deciding on the way whether the two tree-walking examples
are two scenarios or one with named variants.

## Completion criteria
- Each walkthrough in `examples/` (`folder-inventory-to-csv.md`, `flatten-copy-tree.md`,
  `approve-and-copy.md`) opens with the fixed header of `docs/architecture/scenarios/template.md`:
  `Identifier`, `Class`, `Answerers`, `Input data`, `Expected paths`, `Ends with`, `ADRs exercised`.
- The variants question of the two tree-walking examples is decided with alternatives on the table.
- Every named variant is covered by a test or marked as not verified in the walkthrough.
- The `ADRs exercised` lists are derived from the definitions and the tests, not from memory.
- The scenario registry gains one row per example, added on `development` when the branch merges.

## Scope boundaries
- No code, no tests, no changes to the JSON definitions.
- The `support-intake` scenario and the phase exit scenario are not written here.
- No ADR is opened, edited or re-read beyond what the `ADRs exercised` lists need.

## Status
`completed`

## Result
- The three walkthroughs open with the fixed class 4 header; every field is derived from the JSON
  definition and the test suite, and the prose the header absorbed was removed from the body.
- Routes no test drives through the template are marked `not verified` in the headers: the
  `rejected` answer and the `copy_failed` copy of `approve-and-copy`; the empty tree, `copy_failed`
  and the table-write error codes of `flatten-copy-tree`; the table-write error codes of
  `folder-inventory-to-csv`. `copy_failed` is exercised by guard and action unit tests only, which
  does not verify the template's path.
- The three registry rows are ready and land on `development` at the merge, per the registry rule.

## Decisions
- `folder-inventory-to-csv` and `flatten-copy-tree` are two scenarios with one registry row each.
  The alternative — one `tree-walk` scenario with two named variants — was rejected: the class 4
  identifier is the template name, one header cannot serve two walkthrough files, and the variants
  rule covers derivatives of one template, which these two are not; they share an authoring
  skeleton, not a run-time derivation.
- The `not verified` mark is applied to untested expected paths, not only to named variants, so the
  header never claims coverage a test does not give.
- `ADRs exercised` lists the decisions the described run depends on and leaves out the
  infrastructure ADRs every run touches, matching the `repository-interview` calibration.
  `approve-and-copy` does not list ADR 018: the read-surface tests use the template as a fixture,
  but the run the walkthrough describes exercises no read surface.

## Open questions
- Whether the `not verified` paths worth a test (`rejected` on `approve-and-copy`, the empty tree
  on `flatten-copy-tree`) get one in a `test/` session, or stay marked.

## Next steps
1. None pending: the branch was merged into `development` and the registry rows were added in
   their own commit within this session.
2. If the `not verified` paths get their tests, that is its own `test/` session.

## References
- Branch: `docs/class-4-scenario-rows`.
- Changed: `examples/folder-inventory-to-csv.md`, `examples/flatten-copy-tree.md`,
  `examples/approve-and-copy.md`; at merge: `docs/architecture/scenarios/README.md`,
  `docs/sessions/README.md`.
- Related session: `2026-08-23-architecture-1_handoff.md` §5.2 (the decision this session carries
  out); scenario rules: `docs/architecture/scenarios/README.md`.
