# What a version number states: the era, the phase and the fix

- **Date:** 2026-08-25
- **Trigger:** the discussion that followed session `2026-08-25-implementation-5`. Phase 1 was closed
  with a `v0.1.0` tag and phase 2 is expected to close with `v0.2.0`, but no policy says what a
  position of the number means, and the command line publishes no version at all.
- **Status:** open
- **Affected:** ADR 007 (the command that would publish the version), `docs/adr/process.md` (what a
  freeze means once the architecture is refixed), `docs/rules/documentation-rules.md` §6 (superseded
  documentation), `docs/architecture/roadmap.md` (the phases the middle position counts),
  `2026-08-19-installation-and-distribution.md` (no version, no delivery channel)

## The proposal

`vX.Y.Z`, read from the right:

- **Z — a fix inside a released phase.** Defects only; the contract does not move.
- **Y — the phase.** A phase releases code that can already be used. The number of phases is not
  bounded in advance; the roadmap decides what the next one delivers.
- **X — the era: the architecture fixed as final.** Phases are closed; what remains inside the era is
  fixes. A change of X is any architectural change, up to and including changing the implementation
  language.

The clause that matters most is about the decisions, not the digits: **inside one era a frozen ADR
is changed only through another ADR, with the reasoning and the alternatives written out; across an
era boundary the previous corpus stops being binding and becomes the project's knowledge base.**

## What this answers that nothing else does

`docs/adr/process.md` says an accepted ADR is frozen and only superseded. It does not say what
happens to the whole corpus when the architecture is rebuilt: today a rewrite would either drag
every accepted decision with it or silently orphan them. The era boundary gives that event a name and
a rule, and `documentation-rules.md` §6 — remove superseded documentation — gains the exception it
needs, the same way terminal notes are kept as the idea trail.

The consequence to work out: the ADR registry would have to show which era a decision belongs to,
because a reader looking for the rule that binds today must not find a previous era's decision and
take it for law.

## Open questions

- **Does Y keep moving after X reaches 1?** If an era is closed to everything but fixes, an additive
  capability has no place to land short of a new era, which is not plausible for a living tool. Either
  phases continue inside an era — and "phase" must then be defined as something that outlives the
  first fixation — or the era really is frozen and that has to be stated plainly.
- **The scheme is not semantic versioning, and that is free only while X is 0.** Below 1.0 semver
  itself promises nothing, so nothing conflicts. From X=1 on, a breaking change to the CLI contract
  inside an era would move Y, while a consumer of the package reads a moved Y as compatible. Two ways
  out: declare in `README.md` that the project does not follow semver and state what each position
  means, or switch to semver at X=1 and keep the phase as a roadmap concept rather than a digit.
- **Where the number lives.** It is in the package metadata and in the tag; the command line has no
  version flag, and the publication gate already names that as missing. A number that carries this
  much meaning is worth publishing from the tool itself.
- **What closes an era.** "The architecture is final" needs a test as concrete as the phase gates
  have, or X will be moved by mood.
