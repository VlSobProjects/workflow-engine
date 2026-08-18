# Session note

## Type
documentation

## Goal
Add a run/retrieve how-to for the two shipped example templates to the top-level `README.md`, closing
the last open item carried from `2026-08-18-investigation-1` through `2026-08-19-implementation-1`.

## Completion criteria
1. `README.md` documents how to run `examples/folder-inventory-to-csv.json` and
   `examples/flatten-copy-tree.json` end to end, covering both the `init-new-session` /
   `set-input` / `resume` path and the one-shot `run --input`.
2. `README.md` documents how to retrieve the result: `deliverables`, the artifact absolute paths
   surfaced in the command output, `show-state`, and `export-artifact`.
3. `README.md` documents the CLI exit codes (`0`, `2`, `3`, `4`).
4. `README.md` documents the hard node cap: the `workflow_paused_safety_limit` symptom and the
   config-edit-then-resume recovery, matching the frozen phase-1 position in
   `docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md`.
5. Every command shown was actually run against the shipped examples in this session; no invented
   output.

## Scope boundaries
- No code change and no ADR; this is a documentation-only session.
- No `ruff format` pass on the repository; that is a separate open next step.
- No change to the hard cap's scope (host vs. workflow vs. workflow class); that question stays open
  in the architecture note.

## Status
completed

## Result
`README.md` gained a "Running the examples" section covering both entry paths for
`folder-inventory-to-csv.json` and `flatten-copy-tree.json`, a "Retrieving the result" section
(deliverables, absolute artifact paths in command output, `show-state`, `export-artifact`), a CLI
exit codes table, and a "Hitting the hard node cap" section with the `workflow_paused_safety_limit`
symptom and the config-edit-then-resume recovery.

Every command in the how-to was run against a scratch folder outside the repository in this session:
`init-new-session` → `set-input` → `resume` and one-shot `run --input --export-dir` for both
examples, plus `show-state` and `export-artifact --all`. Output shown in the README is trimmed from
those real runs, not invented.

## Decisions
1. The how-to lives in `README.md` under the existing "Running the tests" heading level, not as a new
   document — `docs/rules/documentation-rules.md` reserves `README.md` for "what the project is, what
   it is for, how to run it".
2. Command output in the README is illustrative and trimmed (paths shortened, some fields omitted) to
   stay readable; it is not a byte-for-byte contract test. The CLI contract itself is covered by
   `tests/test_cli_contract.py`, not by the README.

## Open questions
None raised in this session.

## Next steps
1. Decide whether a `chore/` session makes the repository `ruff format` clean (carried from
   `2026-08-19-implementation-1`).
2. The hard node cap scope question stays open in
   `docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md`.

## References
- Branch: `docs/readme-run-and-retrieve-howto`
- Closes the last open item of
  [2026-08-18-investigation-1_handoff.md](2026-08-18-investigation-1_handoff.md), carried by
  [2026-08-19-implementation-1_handoff.md](2026-08-19-implementation-1_handoff.md).
- Related: `docs/architecture/notes/2026-08-19-hard-node-cap-scoping.md`, ADR 007 (CLI contract),
  ADR 011 (artifacts), ADR 012 (inputs).
