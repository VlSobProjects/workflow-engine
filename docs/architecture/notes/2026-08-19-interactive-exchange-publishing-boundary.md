# Where the interactive exchange stops being internal

- **Date:** 2026-08-19
- **Trigger:** architectural review of the delivered ADR 013 implementation (session
  `2026-08-19-implementation-11`), which found no blocking defect but three places where the
  boundary between the engine's internal shapes and the published command contract is held by
  convention rather than by the code
- **Status:** open
- **Affected:** ADR 007 (command contract), ADR 009 (operator help), ADR 013 (delivered), ADR 014
  (Accepted, publishes the same answer declaration), ADR 019 (Draft — its §2 typed question document
  answers §1 and §3 below); the question-rendering note
  (`2026-08-20-question-rendering-for-an-audience.md`) picks up §1's split-the-class option and §3's
  version question with their first real consumer

ADR 013 §3 decided that the caller-facing document is a reduced `question` block, not
`PresentResponse`. The implementation does exactly that, in `answers.question_block`. What the
review points out is that the *decision* is enforced by one function, while the *shapes* around it
still invite the opposite. None of this is a defect in what was built; all of it is what a second
implementation, a second caller, or a second transport would trip over.

**Triaged 2026-08-25 (`2026-08-23-architecture-1` §4, roadmap step 12):** promoted in part. §1 and §3
are answered by ADR 019 §2, the typed question document — a dedicated publishing shape retires
`PresentResponse` as a publishing candidate and gives the block its own version. §2 (`actor` identity)
is not touched by ADR 019 and stays open, alongside the later-phase note
`2026-08-25-role-separation-answerer-and-operator.md`, which is the identity question's first real
consumer. §4 is untouched by any of this.

## 1. `PresentResponse` still looks publishable

The class keeps `submit` and `expected_input`, which describe the unstructured protocol the declared
answer replaced, plus `def_errors`, `SubmitResult` and `SubmitStatus`, which nothing constructs.
ADR 013 removed the two field *defaults* and nothing else, deliberately: the ADR's cost list named
them and the session kept to its scope.

The risk is not today's code, it is the next contributor serializing the dataclass into `data`
because it is right there and has every field a caller could want. That is precisely alternative G,
rejected in the ADR because the same class carries setup errors, budget stops, failures and
completion.

Options, cheapest first:

- **Mark, do not move.** A class docstring stating that `PresentResponse` is internal and that
  `question_block` is the only publisher, plus removing the three unused symbols. Cheap, and it
  survives only as long as people read docstrings.
- **Split the class.** A presentation type for the question and separate report types for the
  budget stop, the setup error, the failure and the completion. This is what makes the boundary
  structural instead of conventional, and it is a change to the engine's return type, so it is an
  ADR, not a cleanup.
- **Keep as is** and rely on the ADR text. Cost: the ADR is the only thing standing between a future
  change and a broken command contract.

## 2. `actor` is a label, not an identity

`actor` is free text (`operator`, `agent:reviewer-bot`, anything). That is the right shape for the
audit story ADR 013 §9 tells: the journal records who *claimed* to answer, next to what was bound.

It becomes wrong the moment anything reads it as an identity: a guard routing on who answered, an
export filtering by actor, a policy allowing only certain actors to approve. Nothing supplies it but
the caller, and nothing verifies it. Before the first such use, the project has to say which of
these it is:

- an audit label, in which case the contract should say so in words, and no component may branch on
  it;
- an identity, in which case it needs a shape (a namespace, a validated pattern), a source of truth
  outside the answer document, and a decision about what an unauthenticated CLI can assert at all.

The second is a much larger decision than it looks: this engine has no notion of a principal, and a
command line has nothing to prove one with.

## 3. The published question has no version of its own

`data.question` is a JSON document consumed by programs, and it carries no version. The command
result as a whole does not carry one either; the operator help payload does (`contract_version`,
ADR 009). Extension is additive by the ADR 007 rule, which covers adding a key but not renaming or
narrowing one.

Worth deciding together, not separately: whether the question block gets its own `schema_version`,
whether the whole command result gets one, or whether the ADR 009 `contract_version` is raised to
cover every machine-readable payload the CLI produces. A per-block version is the cheapest and the
least coherent of the three.

## 4. The invariant that lives outside the engine

ADR 013 §5 says a refused answer journals nothing, and the engine holds that: validation happens
before any event is recorded. The part the engine cannot hold is the other side — a CLI wrapper, an
adapter or an MCP transport that writes its own audit trail would re-introduce exactly the
"something happened to the run" that the refusal denies.

This is not a code change today; it is a rule that belongs in whatever document describes an
integration, and a thing to check when the transport of alternative D is built: the journal has one
writer, the engine.
