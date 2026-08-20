# Session note

## Type
documentation

## Goal
State that committed documentation carries no machine-specific fact, and bring the documents that
already carry one into line with it.

## Completion criteria
- `docs/rules/documentation-rules.md` carries the rule, in the form of the rules around it, with the
  boundary that an illustrative path in an example is not a machine-specific fact.
- The content limits of `docs/sessions/README.md` point to it instead of repeating it.
- No tracked document names a local path that belongs to one machine.

## Scope boundaries
The rule, its two pointers, and the documents that violate it. No change to the `Path` examples of
`README.md` or of the tests, no rule about paths in code, and no new place for machine-local notes.

## Status
completed

## Result
`documentation-rules.md` gained section 8, `No machine-specific facts`: a document states facts about
the project and not about the machine it was written on, a local path, user name, host name or
personal directory is named by its role instead, and a fact true only on one machine lives outside
the repository. The section draws the boundary explicitly, because a scan of the tracked tree showed
the rule would otherwise read as forbidding the illustrative Windows paths that `README.md` and three
tests use to demonstrate separator handling.

The content limits of `docs/sessions/README.md` refer to it, and `CLAUDE.md` carries it in its
condensed summary, since every session type writes a document.

Three session notes were brought into line. Two named the same personal scratch folder
(`2026-08-18-investigation-1`, `2026-08-19-implementation-1`); the third, found by scanning rather
than by the plan, named three absolute paths of one machine as the reason a test could not run
elsewhere (`2026-08-02-implementation-1`). All three now name the role of the folder. The finding
each note recorded is unchanged.

## Decisions
- The rule lives in `documentation-rules.md`, because it binds every document, and every session type
  writes one. `docs/sessions/README.md` gets a pointer, not a copy.
- An illustrative path is explicitly allowed. Without that sentence the rule would condemn correct
  documentation: `README.md` has to show a native Windows path to explain what the `Path` codec
  normalizes, and the value it shows exists on no machine and names no one.
- Machine-local facts are not given a new home inside the repository. The engine of this decision is
  that such facts already have a place outside it; an ignored directory in the tree was considered
  and rejected, because it would be a new location in the closed document map and nothing would read
  it automatically.
- The correction of the three notes is applied to the current documents only. The paths stay in the
  git history, which is accepted: the rule prevents the next occurrence, it does not rewrite the past.

## Open questions
None.

## Next steps
1. Merge `docs/no-machine-specific-facts` into `development` and add the registry row of this session.

## References
- Branch: `docs/no-machine-specific-facts`
- Changed: `docs/rules/documentation-rules.md`, `docs/sessions/README.md`, `CLAUDE.md`,
  `docs/sessions/2026-08-02-implementation-1_handoff.md`,
  `docs/sessions/2026-08-18-investigation-1_handoff.md`,
  `docs/sessions/2026-08-19-implementation-1_handoff.md`
- No ADR is involved. Nothing was executed: the session changed no code.
