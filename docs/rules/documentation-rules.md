# Documentation rules

These rules apply to every documentation change.

## 1. The document map is closed
Only the documents listed below may exist:

| Location | Purpose |
| --- | --- |
| `README.md` | What the project is, what it is for, how to run it |
| `AGENTS.md` | Agent entrypoint, routing only |
| `.github/copilot-instructions.md` | Copilot entrypoint, routing only |
| `docs/README.md` | Documentation index |
| `docs/rules/` | General and task specific rules |
| `docs/architecture/overview.md` | The architecture as it currently is |
| `docs/adr/` | Architecture decision records and their governance |
| `docs/sessions/` | Session notes and the session registry |
| `docs/processes/` | Workflows such as git and documentation |

Creating a document outside this map, or a new kind of document, requires explicit approval first.
The map may change, but only as a deliberate decision.

## 2. Why versus what
- An ADR records why a decision was made, with its alternatives and consequences.
- `docs/architecture/overview.md` records what the architecture is now, without repeating rationale.
- The overview is updated when an ADR becomes Accepted, in the same merge as the implementation.

## 3. One fact in one place
State a fact in a single document and link to it from elsewhere.
Do not copy content between documents.

## 4. Entrypoints stay thin
`AGENTS.md` and `.github/copilot-instructions.md` route to the relevant documents by task type.
They must not carry rule content of their own.

## 5. Format
- Markdown, English, short declarative sentences.
- One topic per document, with a clear title.
- Prefer a list or a table over prose when the content is a set of rules or states.
- Do not pad documents with restated context or summaries of other documents.

## 6. Update or delete
A document that no longer matches reality is corrected or removed.
Do not keep superseded documentation as `archive`, `old`, `notes` or versioned copies.
The only historical record is the ADR history.

## 7. No side documents
Do not write reports, summaries, plans, analyses or work logs into the repository.
Session outcomes belong in `docs/sessions/` in the defined format, and nowhere else.
Working notes stay outside the repository.
