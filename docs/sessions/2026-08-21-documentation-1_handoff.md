# Session note

## Type
documentation

## Goal
Split the example walkthroughs out of `README.md` into `examples/`, leaving the engine contract in
the root document and one line plus a link per template.

## Completion criteria
1. `examples/` is a mapped location in `documentation-rules.md` §1, decided deliberately rather than
   by adding a file outside the map.
2. `examples/README.md` is the registry of the shipped templates and carries what is true of all of
   them; each template has its own document beside its `.json`.
3. The engine contract that lived inside the `approve-and-copy` walkthrough — the answer document,
   the refusal rules, `resume` without an answer, template text, `--input` and the Windows path
   note — stands in the root `README.md` under its own heading, stated once.
4. The root `README.md` example section is a registry pointing into `examples/`, with no walkthrough
   text left behind.
5. Every command and every stated exit code carried across is re-run, not assumed.
6. This session note is completed and committed.

## Scope boundaries
- The ADR-0083 scenario does not join `examples/` here: it is the next session, and it lands in the
  form this one establishes.
- No `.json` template is edited, and no code or test changes.
- The CLI contract itself is not revisited; only where its facts are documented.

## Status
completed

## Result
All six criteria met. `README.md` loses its three walkthrough subsections and gains two contract
sections in their place — "Binding inputs" (with the Windows path note under it) and "Answering an
interactive workflow" — while "Running the examples" becomes a three-row registry linking into
`examples/`. `examples/` gains a registry and one walkthrough per template. The document map, the
merge precondition that names the documentation a branch must carry, and the two documents that
restate it were brought in line.

Everything carried across was re-run rather than assumed: both batch templates in both their
documented forms, the empty-tree failure (`pretty_table_no_data`, exit 3), the missing-target failure
(`target_folder_not_found` under `errors.COPY_FILE`, exit 3), and the interactive template through
its pause (exit 2, the published question block), its approval (exit 0, file copied), its rejection
(exit 0, nothing copied) and its attempts bound (two re-asks, then `max_attempts_exceeded`, exit 3).
Two claims were corrected against what the runs showed rather than kept as written.

## Decisions
1. **The cut is across the subsections, not along them.** The example walkthroughs carried the
   engine's own contract — the answer document, the refusal rules, template text, the `ask` post
   function, `--input`, the Windows path note — because they were explained on `approve-and-copy`.
   Moving the subsections whole would have copied those facts into every walkthrough against
   `documentation-rules.md` §3, so the contract stayed in the root document under its own headings
   and the walkthroughs link to it.
2. **A registry plus one document per template**, rather than one file holding every description: the
   shape the ADR, session and note registries already use, and the shape that survives the ADR-0083
   scenario, which alone is longer than all three current walkthroughs together.
3. **The walkthroughs live beside the definitions**, in `examples/`, not under `docs/`. A template is
   a shipped artifact and its instructions travel with it; `docs/` describes the project.
4. **`docs/README.md` was deliberately not touched.** It indexes the areas inside `docs/`, and no
   root-level location — not `README.md`, not `CLAUDE.md` — is listed there. Adding `examples/` alone
   would have made it a second, partial map. `documentation-rules.md` §1 stays the single map.
5. **The merge precondition had to follow the split.** `git-workflow.md` named `README.md` and the
   overview as the documentation a `feature`/`fix`/`refactor` branch carries; a template's behaviour
   is now documented in `examples/`, so that document is named there too, and in the two places that
   restate the rule (`implementation-rules.md` §11, `CLAUDE.md`).

## Open questions
None.

## Next steps
1. Merge this branch into `development` and add the session registry row.
2. Add the ADR-0083 scenario to `examples/` as the fourth template — an `implementation` session on
   its own branch, since it moves code. What it does: lift the workflow definition out of the
   `WORKFLOW` dict in `tests/test_adr0083_scenario.py` into `examples/`, have the test load the
   shipped file instead of carrying its own copy, so the seven tests already written prove what is
   released; add its walkthrough in the form established here; add its row to the `examples/`
   registry and to the root `README.md` table, marked as waiting for an answer. It is the first
   shipped template that pauses more than once, so its walkthrough carries the sequence of answers,
   while the answer document itself stays where this session put it. Its `S` step — what a receiving
   process does with the collected result — stays outside by the decision of session
   `2026-08-21-architecture-2`, so the template ends at its exported deliverable.

## References
- Branch: `docs/readme-examples-split`
- Changed: `README.md`, `examples/README.md`, `examples/folder-inventory-to-csv.md`,
  `examples/flatten-copy-tree.md`, `examples/approve-and-copy.md`,
  `docs/rules/documentation-rules.md`, `docs/rules/implementation-rules.md`,
  `docs/processes/git-workflow.md`, `CLAUDE.md`, this note
- Previous session: `2026-08-21-architecture-2_handoff.md`
