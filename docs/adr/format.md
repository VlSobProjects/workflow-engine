# ADR format

Formatting rules for an individual ADR document.

## File name
`adr-<number>-<short-name>.md`

- The number is three digits and is never reused.
- The short name is lowercase ASCII with hyphens and names the decision.
- Example: `adr-001-exception-architecture.md`, worked on in `feature/adr_001-exception-architecture`.

## Structure
Use the section order defined in `template.md`.

## Status values
Use exactly one of: `Draft`, `POC`, `Implementing`, `Accepted`, `Superseded`, `Rejected`.
Status semantics and transitions are defined in `process.md`.

## Content rules
- Cover one decision per document.
- Name the decision in the title.
- Keep Context, Decision and Consequences factual and short.
- List the alternatives that were actually considered, with their trade-offs.
- Link related and superseded ADRs explicitly.
- Record meaningful changes in the change log while the ADR is not frozen.
- Once the ADR is Accepted, the text describes the delivered result and is no longer edited.
