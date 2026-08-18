# Session note

## Type
documentation

## Goal
Apply the documentation-only corrections recorded by
`docs/sessions/2026-08-19-investigation-1_handoff.md` (findings A.1, A.2 doc part, B, C, D, E except
E.6) so the documentation matches the code and the three registries are consistent, before the
phase 1 tag.

## Completion criteria
1. The 8 sessions found unregistered in the audit have a row in `docs/sessions/README.md`.
2. `README.md` states the `flatten-copy-tree` precondition, uses `uv run pytest`, and notes the long
   codec name form.
3. `docs/architecture/overview.md` matches the code for every point in finding B.
4. ADR files and process docs match findings D.1-D.5.
5. Session notes missing template headings (E.2) are completed; the architecture notes template
   heading style (E.3) matches the existing notes.
6. `CLAUDE.md` is added to the document map as a stated-exception entrypoint (E.4);
   `.github/copilot-instructions.md` routing matches `AGENTS.md` (E.5).
7. `uv run ruff check .` and `uv run ruff format --check .` are clean (no code changed, so `pytest` is
   not required per the verification rule).

## Scope boundaries
- No code change: the `copy_file` behaviour defect (finding A.2, code part) is a separate `fix/`
  session.
- Merged branch deletion (finding E.6) is not documentation and is left to the user.
- Preventive rules (investigation open question 3) are not written here; that is its own follow-up.
- Frozen ADR decision text (Context/Decision/Consequences) is not touched, only status labels, links
  and template structure, which `docs/adr/process.md` allows on an Accepted ADR.

## Status
completed

## Result
All completion criteria items applied; see Decisions and the file list in References.

## Decisions
1. CLAUDE.md (E.4): added to the document map in `docs/rules/documentation-rules.md` §1 as an
   entrypoint, with a stated exception letting it also carry a condensed rules/commands summary for
   Claude Code's own use, instead of thinning it to routing-only. User's explicit choice.
2. D.4 contradiction (`docs/adr/process.md` "a Draft ADR is written directly on `development`" vs.
   `docs/processes/git-workflow.md`'s direct-commit exception list): resolved by extending the
   git-workflow.md exception list to include opening or editing a Draft ADR, matching actual practice
   throughout the session registry (every Draft ADR to date was opened directly on `development`).
3. D.1/D.2 ADR text fixes (stale cross-reference status labels, "Planned branch" wording, template
   heading deviations, `—`/`None` empty-value inconsistency, missing "frozen as Accepted" change log
   entries) are treated as the "editorial fixes, status and links" `docs/adr/process.md` allows on an
   Accepted ADR, not as reopening the decision.
4. E.3 (notes template heading style): fixed `docs/architecture/notes/template.md` to `# <title>` to
   match all three existing notes, rather than rewriting the notes to `##`.

## Open questions
None beyond the investigation's open question 3 (preventive rules), left to its own follow-up.

## Next steps
1. Delete the merged branches listed in the investigation (finding E.6).
2. Open a `fix/` session for `copy_file` with a non-existent target directory (finding A.2, code
   part).
3. Merge `development` into `main` and tag `v0.1.0` once the above and this session are merged.
4. Decide and write the preventive rules (investigation open question 3).

## References
- Branch: `docs/phase1-audit-doc-fixes`
- Source audit: `docs/sessions/2026-08-19-investigation-1_handoff.md`
- Files changed: `docs/sessions/README.md`, `README.md`, `docs/architecture/overview.md`,
  `docs/adr/adr-007-cli-contract-and-session-lifecycle-for-v1.md`,
  `docs/adr/adr-008-runtime-directory-and-default-path-policy-for-v1.md`,
  `docs/adr/adr-009-operator-help-and-component-introspection-contract.md`,
  `docs/adr/adr-010-session-safety-cap-and-unbounded-run-policy.md`, `docs/adr/adr-011-*.md`,
  `docs/adr/adr-012-*.md`, `docs/adr/adr-002-node-composition.md`,
  `docs/adr/adr-003-persistence-and-workspace.md`, `docs/adr/README.md`, `docs/adr/process.md`,
  `docs/processes/git-workflow.md`, `docs/architecture/notes/template.md`, `CLAUDE.md`,
  `docs/rules/documentation-rules.md`, `.github/copilot-instructions.md`, and the session notes listed
  under finding E.2.
