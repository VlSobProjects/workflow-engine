# Session note

## Type
documentation

## Goal
Bring `README.md` and `docs/architecture/overview.md` back in line with the four `v0.1.0` fix
sessions, and write down the rule that would have made this session unnecessary.

## Completion criteria
1. Every statement the four fix sessions made inaccurate or incomplete is corrected, in both
   documents.
2. A short rule states that a `feature/`, `fix/` or `refactor/` branch carries the documentation its
   change made inaccurate, in the same branch.
3. The rule is stated in one place and linked from the others, per documentation rules §3.

## Scope boundaries
- No code change; nothing in `src/` or `tests/` is touched.
- No new document and no change to the document map.
- The `v0.1.0` tag move is a separate step, after this session.

## Status
completed

## Result
No executable file changed, so neither pytest nor ruff was run; there was nothing they could catch.
The documentation edits were checked by reading the code they describe.

Five statements corrected:
- `README.md`, the `--export-dir` bullet: the result now reports `data.export` with the destination
  and the exported map, and when the key is absent.
- `README.md`, the exit-code paragraph: a malformed command line writes to stderr and, under
  `--json`, still answers on stdout.
- `overview.md`, the artifact export section: the terminal result carries the destination, not only
  the `artifacts_exported` event.
- `overview.md`, "the CLI is the only writer of standard output": the claim now also covers the
  argument parser, which was the one path that broke it.
- `overview.md`, the operator help contract: what `source` means, and that a codec is addressed by
  the ADR 012 name rule on this surface too.

The rule lives in `docs/processes/git-workflow.md` under the merge preconditions, next to the tests
and the registries. `docs/rules/implementation-rules.md` gains §11 pointing at it, which renumbers
the former §11 to §12; nothing references those sections by number. The condensed rule list in
`CLAUDE.md` gains the same line, as documentation rules §4 requires of that summary.

## Decisions
1. The rule names `docs/architecture/overview.md` as well as `README.md`. Three of the five
   corrections in this session were in the overview, and `documentation-rules.md` §2 only requires
   the overview to be synchronized at an ADR freeze, which none of the four fix sessions was.
2. The rule is a merge precondition in `git-workflow.md`, not a rule of its own in
   `implementation-rules.md`. It has the same shape as the preconditions already there — tests, the
   linter, the registries — and stating it twice would breach documentation rules §3.
3. This session is typed `documentation` because it changes no code. Going forward the same work
   belongs inside the implementation session that caused it; that is what the new rule says.

## Open questions
None.

## Next steps
1. Move the `v0.1.0` tag: merge `development` into `main`, re-point the annotated tag at the new
   `main` commit and force-push it, then push both branches. `pyproject.toml` stays at `0.1.0`.
2. Once a GitHub Release or a published package exists, the tag becomes immutable and the next batch
   of fixes takes a new version. The release procedure itself is still unwritten and stays with
   `docs/architecture/notes/2026-08-19-installation-and-distribution.md`.

## References
- Branch: `docs/v0_1_0-fix-followups`
- Sessions it documents: `2026-08-19-implementation-6`, `2026-08-19-implementation-7`,
  `2026-08-19-implementation-8`, `2026-08-19-maintenance-1`
- Documents changed: `README.md`, `docs/architecture/overview.md`,
  `docs/processes/git-workflow.md`, `docs/rules/implementation-rules.md`, `CLAUDE.md`
