# Documentation rules

These rules apply to every documentation change.

## 1. The document map is closed
Only the documents listed below may exist:

| Location | Purpose |
| --- | --- |
| `README.md` | What the project is, what it is for, how to run it |
| `examples/` | The shipped workflow templates: a registry of them and one walkthrough per template, beside the definitions themselves |
| `AGENTS.md` | Agent entrypoint, routing only |
| `.github/copilot-instructions.md` | Copilot entrypoint, routing only |
| `CLAUDE.md` | Claude Code entrypoint; routes like `AGENTS.md`, plus a condensed non-negotiable-rules/commands summary for Claude Code's own use (stated exception to §4, kept in sync with the documents it summarizes) |
| `docs/README.md` | Documentation index |
| `docs/rules/` | General and task specific rules |
| `docs/architecture/purpose.md` | What the engine is for, its boundaries and what counts as done; read at the start of every architecture session |
| `docs/architecture/overview.md` | The architecture as it currently is |
| `docs/architecture/notes/` | Architecture notes and their registry: durable ideas not yet decided |
| `docs/adr/` | Architecture decision records and their governance |
| `docs/sessions/` | Session notes and the session registry |
| `docs/processes/` | Workflows such as git and documentation |

Creating a document outside this map, or a new kind of document, requires explicit approval first.
The map may change, but only as a deliberate decision.

## 2. Why versus what
- An ADR records why a decision was made, with its alternatives and consequences.
- `docs/architecture/overview.md` records what the architecture is now, without repeating rationale.
- The overview is updated when an ADR becomes Accepted, in the same merge as the implementation.
  This is a freeze gate condition: see the freeze gate in `docs/adr/process.md`.

## 3. One fact in one place
State a fact in a single document and link to it from elsewhere.
Do not copy content between documents.

## 4. Entrypoints stay thin
`AGENTS.md` and `.github/copilot-instructions.md` route to the relevant documents by task type.
They must not carry rule content of their own.
`CLAUDE.md` routes the same way but is exempt from this rule: it may also carry a condensed
non-negotiable-rules/commands summary for Claude Code's own use, per the map entry in §1. Keep that
summary in sync with the documents it draws from; it does not replace them as the source of truth.

## 5. Format
- Markdown, English, short declarative sentences.
- One topic per document, with a clear title.
- Prefer a list or a table over prose when the content is a set of rules or states.
- Do not pad documents with restated context or summaries of other documents.

## 6. Update or delete
A document that no longer matches reality is corrected or removed.
Do not keep superseded documentation as ad hoc `archive`, `old` or versioned copies.
The historical record is the ADR history and the architecture notes trail
(`docs/architecture/notes/`, retained per its own README, not this rule).

## 7. No side documents
Do not write reports, summaries, plans, analyses or work logs into the repository.
Session outcomes belong in `docs/sessions/` in the defined format, and nowhere else.
Durable architectural ideas that are not yet decisions belong in `docs/architecture/notes/`, in the
format defined by its README — the single sanctioned in-repo channel for architectural thinking.
Ephemeral working notes stay outside the repository.

## 8. No machine-specific facts
Committed documentation states facts about the project, not about the machine it was written on.
Never write a local path, a user name, a host name or a personal directory into a document; name the
role of the thing instead, such as "a scratch folder outside the repository".
A fact that is true only on one machine lives outside the repository.
An illustrative path in an example is not a machine-specific fact: it names no one and exists nowhere.
