# Session note: 2026-08-25 documentation 3

## Type
`documentation`

## Goal
Execute the notes triage `2026-08-23-architecture-1` §4 decided, and settle the rename of
`test_adr0083_scenario.py` with the note it was named beside (roadmap step 12).

## Completion criteria
- Every note under "Not triaged" in `docs/architecture/notes/README.md` is closed, dropped, or moved
  to a phase section — none left untriaged.
- The two-note "three open choices" from the 2026-08-24 resumption (drop `node-save-as-redundancy`,
  close `adr0083-scenarios-coverage` as promoted, keep `support-intake` open) are applied exactly.
- `test_adr0083_scenario.py` and `2026-08-19-adr0083-scenarios-coverage.md` are renamed, dropping the
  reserved word "scenario"; every currently open document that links to the note follows the rename.
- `docs/architecture/roadmap.md` step 12 reads `done`.
- `uv run pytest` and `uv run ruff check .` stay clean.

## Scope boundaries
- No new ADR content and no ADR status change; the two `Affected` additions (ADR 019 on two notes)
  record an existing relationship, not a new decision.
- No behaviour change: the two file renames carry no logic edit beyond the self-referential path in
  their own docstrings.
- Frozen ADRs (`adr-015`, `adr-017`) and every historical `docs/sessions/*_handoff.md` file that cites
  either old filename are left untouched — they are accurate history of what was true when written,
  not dangling links to fix.

## Status
`completed`

## Result
`docs/architecture/notes/README.md`'s "Not triaged" section is now empty. Of the eleven notes:
- **Closed** — `2026-08-19-adr0083-coverage.md` (renamed from `...-scenarios-coverage.md`) as
  `promoted → ADR 015, 016, 017`; `2026-08-19-node-save-as-redundancy.md` as `dropped`.
- **Later phases** — the other nine, all of them either named explicitly in the current
  `docs/architecture/roadmap.md` phase-3 work list or on its "Not now" list: `support-intake-use-case`,
  `agent-instruction-and-skill`, `interactive-exchange-publishing-boundary`, `adr012-deferred-questions`,
  `recovery-and-resilience-roadmap`, `installation-and-distribution`, `engine-as-team-process-carrier`,
  `hard-node-cap-scoping`, `entry-point-discovery`.

Five notes got a body edit beyond the registry move, each traced to a specific line of §4 or of the
gap table: `node-save-as-redundancy` and `adr0083-coverage` record their closing `Status`;
`interactive-exchange-publishing-boundary` records §1/§3 promoted in part into ADR 019 §2, §2 (actor
identity) left open; `adr012-deferred-questions` records §2 as settled inside ADR 019 by a different
mechanism than the note proposed (a per-codec schema fragment and example, not the canonical-short-name
alias); `engine-as-team-process-carrier` records the §1 correction that it is a later application, not
the purpose. The other six notes needed only their registry row moved.

`test_adr0083_scenario.py` → `test_adr0083_coverage.py`; `2026-08-19-adr0083-scenarios-coverage.md` →
`2026-08-19-adr0083-coverage.md`. Every living reference to the old names now points to the new ones:
both renamed files' own docstrings, `test_answer_functions.py`, `test_bounded_accumulating_loop.py`,
and the two still-open notes that linked the note by path (`engine-as-team-process-carrier.md`,
`support-intake-use-case.md`). The registry row moved and its link updated as part of the close.

`uv run pytest` and `uv run ruff check .` both clean after the renames.

## Decisions
1. **Phase placement follows the current roadmap, not the roadmap shape of 2026-08-23.** §4's own text
   has no phase column; it was written before `2026-08-25-architecture-2` moved all authoring-surface
   work to a new phase 3 and `2026-08-25-documentation-2` reordered what stayed in phase 2. Every note
   that lands in "Later phases" here does so because the *current* roadmap names it there (phase 3's
   explicit work list, or the "Not now" list), not because §4 said so directly — §4's substance (what
   each note still needs) is unchanged, only which section holds it.
2. **The rename went ahead despite two frozen ADRs citing the old exact paths.** `adr-015` and `adr-017`
   (both Accepted) cite `tests/test_adr0083_scenario.py` and, in `adr-015`'s case, the old note path, as
   evidence in their own text and change log. Per `adr-rules.md` rule 6, a frozen ADR is not edited to
   chase a rename elsewhere — those citations stay exactly as they were true when each ADR froze, the
   same way roughly twenty historical session notes that also mention the old names are left alone.
   Only documents still capable of changing — the registry, other open notes, and the two living test
   files — were updated.
3. **`adr012-deferred-questions` §2 is settled by a different mechanism than it proposed.** The note's
   own direction was a canonical short codec name replacing the Python-version-dependent full name.
   Reading ADR 019 §5 found it does not build that: it publishes a schema fragment and an example per
   codec instead, which moots the urgency (a bare codec name is no longer what an answerer has to act
   on) without adopting the proposed design. The note is annotated with what actually settled it, not
   with the direction it once favored.

## Open questions
None.

## Next steps
1. Roadmap step 13: the live-model rehearsal of the `reorganize-folder` plan variant.

## References
- Branch: `docs/roadmap-step-12-notes-triage`
- Session driving this one: `2026-08-23-architecture-1` §4, and its open question in
  `2026-08-25-implementation-7`.
- Documents changed: `docs/architecture/notes/README.md`, `docs/architecture/notes/2026-08-19-adr0083-coverage.md`
  (renamed), `docs/architecture/notes/2026-08-19-node-save-as-redundancy.md`,
  `docs/architecture/notes/2026-08-19-interactive-exchange-publishing-boundary.md`,
  `docs/architecture/notes/2026-08-18-adr012-deferred-questions.md`,
  `docs/architecture/notes/2026-08-19-engine-as-team-process-carrier.md`,
  `docs/architecture/notes/2026-08-21-support-intake-use-case.md`, `docs/architecture/roadmap.md`,
  `docs/sessions/README.md`; `tests/test_adr0083_scenario.py` renamed to `tests/test_adr0083_coverage.py`,
  `tests/test_answer_functions.py`, `tests/test_bounded_accumulating_loop.py`.
- Related ADRs: ADR 015, 017 (Accepted, cited by the renamed files, left untouched), ADR 019 (Draft,
  newly named in two notes' `Affected`), ADR 020 (Accepted, the drop reason for `node-save-as-redundancy`).
