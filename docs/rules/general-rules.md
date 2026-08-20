# General rules

These rules are binding for every task in this repository.
They are intentionally short. Details live in the linked documents.

## 1. Language
All artifacts committed to this repository must be written in English:
documentation, code, identifiers, comments, commit messages, branch names, ADRs, session notes.
This is not negotiable.
The conversation language with the user is free and does not affect this rule.

## 2. Branches
Never commit directly to `main`.
Every change is made in a branch created from `development`.
Leave no file that is neither tracked by git nor ignored.
Branch categories, naming, lifecycle, merge rules and working tree hygiene: see `docs/processes/git-workflow.md`.

## 3. Architecture discussions
Architecture is discussed in critical mode, not in agreement mode.
Minimum requirements: state at least two alternatives, name the trade-offs, and state the cost of the change.
Architectural work happens under an ADR: the decision is written first, then proven by a POC or an implementation, and only then frozen.
An accepted ADR is frozen and is changed only by superseding it.
Details: see `docs/rules/adr-rules.md` and `docs/adr/process.md`.

## 4. Session scope
Every session declares its type, its goal and its completion criteria in its session file before work starts.
Keep the scope as narrow as possible; split large tasks into several sessions instead of widening one.
If the scope grows during the session, stop and propose a split.
Every session ends with a completed session note containing the next steps.
Details: see `docs/sessions/README.md`.

## 5. Document creation
Documents are created only inside the approved documentation structure.
Creating a new kind of document, or a document outside the structure, requires explicit approval first.
The structure may change, but only as a deliberate, justified decision.
Generating ad hoc documents, summaries or alternative formats is forbidden.
Details: see `docs/rules/documentation-rules.md`.

## 6. No scope creep
Change only what the task requires.
Do not touch unrelated files and do not fix unrelated problems without asking first.

## 7. Verification
Before reporting a task as done, run the relevant tests and linter.
Never claim success that was not verified.
State explicitly what was executed and what was not.

## 8. Ask instead of guessing
When the task is ambiguous or a decision has several reasonable outcomes, ask a short, specific question.
Do not silently choose for the user.

## 9. Dependencies
Keep external dependencies minimal.
A new dependency requires justification and explicit approval.

## 10. Information economy
Spend research effort where it pays off.
Do not run long code searches for information the user can provide immediately, and do not ask trivial questions that a quick look at the code answers.
Know the limits of your own knowledge: for facts that change over time, such as library versions, releases or current APIs, verify them from documentation or the internet instead of relying on memory.
When unsure whether to search or ask, ask.

## 11. Finish open architecture work first
Do not open a new ADR in POC or Implementing while another ADR is still in POC or Implementing.
The only exception is an ADR that turned out to be a dependency of the work in progress.
Such a dependency must be recorded in the `Depends on` column of the ADR registry.
Drafts are not affected by this rule and may stay open.

## 12. Commit confirmation
A commit is never made without the user seeing its message first.
Present the complete message, subject and body, and wait: the user confirms it, corrects it, or makes
the commit themselves.
The message is presented as a file, so that it can be read, copied and extended without being retyped.
This covers every commit, a merge commit and a one line registry commit included.
The form of the message is defined in `docs/processes/git-workflow.md`.
