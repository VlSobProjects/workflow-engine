# 2026-10-05-documentation-1

## Type
`documentation`

## Goal
Put this project on the shared exchange desk: state the desk's rules in this project's process
documents, as asked by the desk letters EX-1 (2026-10-05, the desk opens) and EX-4 (2026-10-05, two
amendments to the desk's rules).

## Completion criteria
- Each of the eight desk rules has a verdict, with one reason, weighed against this project's rules.
- The tracked documents were searched for every place that states how this project corresponds with
  other projects, and the result is recorded.
- The rules are written in one process document, and every entrypoint routes to it.
- The branch is merged into `development` and the session registry carries its row.
- Outside the repository: the answer to EX-1 is a `draft` on the desk, and EX-4 names in its
  `What it changed` where its two amendments were written.

## Scope boundaries
- Past session notes and decision records are history and are not edited.
- No letter is released: the status and the release date of a letter belong to the user.
- The desk itself, its fields and other projects' letters are not changed.
- No code changes.

## Status
`completed`

## Result
- Verdicts: all eight rules accepted, none changed and none rejected. Rule 1 agrees with one fact in
  one place, rule 2 with the commit confirmation of general rule 12, rule 4 with session scope and
  no scope creep, rule 5 with the frozen-and-superseded ADR model, rule 6 with never claiming
  unverified success, rule 7 with the rule against machine-specific facts. Rules 3 and 8 meet
  nothing in this project that they contradict.
- Search: no tracked document stated how this project corresponds with other projects. The only
  mentions were in the `2026-08-28-architecture-1` session note and its registry row, which are
  history. This project never kept an `exchange/` folder, so `.gitignore` is unchanged.
- `docs/processes/exchange-desk.md` states the eight rules and how a session of this project works
  the desk. `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md` and `docs/README.md` route to
  it; `CLAUDE.md` also carries the release rule among its condensed rules.

## Decisions
- The desk rules live in `docs/processes/`, the map's slot for workflows, not in
  `docs/rules/general-rules.md`: they govern one activity, and the general rules stay short.
- Work on the desk is session work: a session whose only output is a letter still leaves a session
  note, because the desk is outside git and the note is the project's record that the letter exists.
- A committed document cites a letter by its identifier, date and subject, never by the desk's
  address.

## Open questions
None.

## Next steps
1. The user releases the answer to EX-1 on the desk.
2. A later session that answers a letter follows `docs/processes/exchange-desk.md`.

## References
- Branch: `docs/exchange-desk`
- Changed: `docs/processes/exchange-desk.md` (new), `AGENTS.md`, `CLAUDE.md`,
  `.github/copilot-instructions.md`, `docs/README.md`
- Outside this repository: the desk letters EX-1 and EX-4, and the draft answer to EX-1
