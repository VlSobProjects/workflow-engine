# Session 2026-11-21-architecture-1

## Type
architecture

## Goal
Separate the public visibility of the repository from the `publication` gate of the roadmap, so the
repository can be opened for reading during phase 2 as the desk letter EX-44 asks, without moving the
gate of a release.

## Completion criteria
- The `publication` row of `roadmap.md` gates a release and no longer names the licence.
- `roadmap.md` states that visibility is not the gate, that the public face is the default branch
  `development`, and that `main` stays the line of marked stable states.
- `purpose.md` no longer reads as if a live run gated the visibility of the repository.
- At least two alternatives are recorded with their cost.

## Scope boundaries
- No README, licence, history scan or motivation change: those are the documentation session that
  follows.
- `main` is not touched.
- No ADR is opened or edited; no note is triaged.
- The repository settings and its visibility are changed by the owner, not by this session.

## Status
`completed`

## Result
- `roadmap.md`: the `publication` exit row names the live run, the version flag and the delivery
  channel, and no longer the licence; a paragraph under the phases table states that the row gates a
  release, not visibility, that a reader lands on `development`, and that `main` stays the line of
  marked stable states.
- `purpose.md`: the live run is named the gate for a release instead of for publication.

## Decisions
1. **Visibility and release are two things; only the release is gated.** EX-44 asks for the
   repository to be public during phase 2, as a portfolio piece with an honest status line. The
   roadmap row bundled visibility with what makes a release usable — a live run, a version, a
   channel. Alternatives considered:
   - *An ADR recording a one-time exception* — rejected: ADRs here decide the engine's architecture,
     and an exception leaves the bundled gate in place to be argued again at the next question.
     Cost would have been one more ADR with nothing to implement.
   - *Refusing until the gate passes* — rejected: it delays the purpose of being read for months
     while the gate's own conditions concern operators, not readers.
   - *Rewording the row* (chosen) — one row and one paragraph; the gate keeps its meaning for the
     moment a release exists.
2. **The licence leaves the gate.** A licence is what makes a readable repository usable at all, so
   it belongs to visibility; it is added by the documentation session that follows.
3. **`main` is not merged for the opening.** A reader sees the default branch `development`; `main`
   keeps its meaning as the line of marked stable states, merged at a phase close or a release. The
   alternative — merging `development` into `main` now so that `main` carries the licence — would call
   a mid-phase state stable, which `main` has never meant.

## Open questions
- None.

## Next steps
1. The documentation session on its own branch: the README entry block, the MIT licence, the
   motivation paragraph on agent operability, the full-history scan and the clean-clone check; it
   also updates the `installation-and-distribution` note row, which still lists the missing licence.
2. The owner merges, pushes and switches the repository to public with its description and topics.
3. A `notice` to JobSearch as a draft on the desk, and `What it changed` of EX-44 filled after the
   merge.
4. On merge: add this session's registry row on `development`.

## References
- Branch: `docs/publication-gate-split`
- Desk letter: EX-44 (2026-11-21, prepare the repository for public release)
