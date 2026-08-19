# Session note

## Type
documentation

## Goal
Apply the documentation findings of `2026-08-19-investigation-2`: the `set-limit` wording (2), the
README precondition for running the CLI (5), the Windows path note (9), the architecture overview
imprecisions (10) and the rules, index and registry defects (11).

## Completion criteria
1. Every statement listed in findings 2, 5, 9, 10 and 11 that concerns a document matches the code
   that was read while fixing it.
2. `docs/rules/implementation-rules.md` has no duplicate section number, and `docs/rules/README.md`
   routes to the right paths.
3. The ADR registry states what `Depends on` means, so it no longer reads as a contradiction of the
   frozen `Related ADRs` sections.
4. No file outside the document map is touched, so the code checkers stay unrun by design.

## Scope boundaries
- Documents only: `README.md`, `docs/architecture/overview.md`, `docs/rules/*`, `docs/adr/README.md`,
  `CLAUDE.md`. No code, no ADR body: an accepted ADR is frozen.
- Findings 6, 7 and 8 are code behaviour and stay out; finding 6 is already held by the open note
  `2026-08-18-adr012-deferred-questions.md`.
- The two repository-hygiene items inside finding 11 (the BOM in `.gitignore`, the Cyrillic strings in
  `tests/test_json_storage.py`) belong to a chore session, not here.
- The session-note H1 variation inside finding 11 is left alone: the template does not prescribe an
  H1, so the notes are not in breach of anything.

## Status
completed

## Result
`docs/architecture/overview.md`, against the code read while fixing each line:

- `set-limit` refuses any value below the current *limit*, with `0` as the one exception; the nodes
  already visited do not enter the rule (`engine.py:505-517`, finding 2).
- An error is a value in the action result, and an exception that escapes the action reaches the
  engine, which ends the run as failed.
- The `attempts` allowance is `max_attempts`, default `3`; when it is spent a self-targeting
  transition fails the node under `max_attempts_exceeded`, while a transition carrying `attempts`
  towards another node finally takes that route (`engine.py:114-123`).
- A guard name is the error code only through the `validators` expansion; a routing node that matches
  nothing fails under the action's code or `no_transition_matched` (`engine.py:30,145`).
- An explicit and a declared input type must resolve to the same codec (`inputs.py:47-59`), and an
  unbound required input journals `workflow_setup_failed` with the missing names (`engine.py:591-605`).
- Any resolved config path is created when no file is there, an explicit `--config` path included
  (`config_loader.py:183-206`).
- A guard detail payload adds `kind`, a codec detail adds `python_type`.

`README.md`: what the `workflow-engine` command needs before any example runs, verified in a shell
without the repository venv (finding 5); the same config-creation correction (finding 10); a note on
the Windows path limit an operator meets as `pretty_table_write_error` with `[Errno 2]` (finding 9).

`CLAUDE.md`: the guard description no longer says guards never see the state; they receive a read-only
view that resolves `param.`/`output.`/`artifact.` references, and the predicate function gets the
resolved values.

`docs/rules/implementation-rules.md`: the second `## 10.` is now `## 11.`.
`docs/rules/README.md`: correct relative paths, and the same routing the `AGENTS.md` entrypoint uses.
`docs/adr/README.md`: `Depends on` is defined as the hard dependency the general rule 11 reads, and is
explicitly not a mirror of the frozen `Related ADRs` section.

Verification: no code file was touched, so pytest and ruff were not run in this session; the last run
on `development` (255 passed, ruff clean) still holds.

## Decisions
1. The divergence between `Depends on` and `Related ADRs` is closed by defining the two, not by
   editing either side: the ADR files are frozen, and the column carries a narrower meaning on purpose.
2. The Windows path limit is documented as an operating condition next to `work_dir` rather than
   treated as a defect.
3. The session-note H1 variation is not a finding: the template prescribes no H1.

## Open questions
None.

## Next steps
1. Merge into `development` and register the session.
2. Remaining audit follow-ups, all outside documentation: findings 6, 7 and 8 (help-component name
   resolution, the `source` of a component loaded by a launcher script, `--export-dir` reporting), the
   BOM in `.gitignore` and the Cyrillic strings in `tests/test_json_storage.py`, plus the two findings
   opened by `2026-08-19-implementation-4` (the `FunctionRuntimeError` message, the uncalled
   `load_all_states` pair).
3. Phase 1 tag `v0.1.0`.

## References
- Branch: `docs/phase1-audit-doc-followups`
- Audit findings: `2026-08-19-investigation-2_handoff.md`, findings 2, 5, 9, 10, 11
- Changed: `README.md`, `docs/architecture/overview.md`, `docs/rules/README.md`,
  `docs/rules/implementation-rules.md`, `docs/adr/README.md`, `CLAUDE.md`
