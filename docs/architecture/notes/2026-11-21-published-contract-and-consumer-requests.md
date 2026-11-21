# The published contract and how a consumer asks for a change to it

- **Date:** 2026-11-21
- **Trigger:** session `2026-11-20-documentation-1`, writing the scenario `model-call-reading` for
  `llm-test-bench` (EX-37, 2026-11-18, llm-test-bench joins the desk): the bench listed among the
  surfaces it relies on a file of the storage backend, and the discussion turned to what the engine
  promises at all, to whom, and how that promise survives a second storage backend and publication.
- **Status:** `open`
- **Affected:** ADR 005, ADR 007, ADR 009, ADR 011, ADR 012, ADR 014, ADR 018, ADR 021,
  `docs/processes/exchange-desk.md`, `documentation-rules.md` §1, the notes
  `2026-08-25-version-numbering-and-architecture-eras`, `2026-08-19-installation-and-distribution`,
  `2026-08-28-authoring-extends-to-components`, `2026-11-21-storage-read-contract`

## The tension

What the engine gives a consumer is described in prose across `README.md`, the overview, the help
surface and docstrings, and nothing checks that the output matches the prose. A consumer therefore
learns what it may rely on by reading the engine's files, and relies on what it finds there — the
bench on `workflow.json`, which a database backend will not have. The engine has three consumers that
build on it now (`llm-test-bench`, the reconciliation POC, the load-test triage of phase 2) and will
have unknown ones after publication. A consumer pins a commit because nothing else is safe.

## The direction agreed in the discussion

- **The engine writes the contract.** A contract is a promise of the engine, so the engine sets its
  form and its content. A consumer never writes it.
- **A consumer asks by a request.** What a consumer needs and the contract does not give it, it asks
  for by a letter of kind `request`. The engine weighs it under its own rules (purpose, ADR process,
  no scope creep), then implements it or refuses with the reason, and answers. A letter is a request,
  never an instruction (desk rule 4); this only names the contract as what a request changes.
- **A consumer declares what it uses.** Its scenario lists the surfaces it takes, each marked contract
  or implementation, as `model-call-reading` does. Use of a surface outside the contract is visible at
  once and answered with "not a surface".

## The levels of the contract

| Level | What | Who uses it | Cost of freezing it |
| --- | --- | --- | --- |
| T1 | The command line and its outputs: the command result per command, the node record, the codec envelope, exit codes, the configuration file | every consumer | medium; checkable by tests over JSON |
| T2 | The definition format: nodes, `action_type`, `action_parameters` per action, transitions, guards, `inputs`, `deliverables` | every author of a workflow; phase 3 demands "the published surfaces alone" | medium; a schema of the definition |
| T3 | The component API: the registration decorators, what a function, a validator and a codec receive and return, the provider adapter contract (`ProviderCall`, `ProviderReply`, the error classes, `finalize`) | the bench's task packages, the POC's parsers and validators, any third-party adapter | high: a Python API with no type checker, checkable only by a sample plugin package under test |
| — | Internals: the engine, the models, `StateModel`, the storage files, `Storage` as a class | nobody outside | not published |

T3 also wants one document for the author of a component: today it is spread over `README.md`
("Writing a custom function"), `help-component` and docstrings.

What every storage backend must give a reader is a level of its own: the note
`2026-11-21-storage-read-contract`.

## How a contract is checked

- **A.** Prose, as now, and the consumers' scenarios. Costs nothing; checks nothing.
- **B.** Consumer-driven tests: fixed outputs of `fake` runs for the surfaces the scenarios list. Small
  to medium; checks only what is used; fixed outputs are brittle and catch harmless changes too.
- **C.** Published schemas — the command result per command, the record, the codec envelope, the
  configuration, the definition — with a schema version in the output, and tests that hold the real
  output against them. Medium, and every change of an output touches its schema; validating a schema
  in tests is a development dependency to be approved.
- **D.** C plus a compatibility policy: what counts as a breaking change, which position of the
  version moves for it, and the version printed by the command line. Needs the decision the
  version-numbering note prepares.

The same contract tests, run against every storage backend, are the evidence that a second backend
changed nothing for a consumer; so the contract comes before the database backend, and passing the
tests on it is that backend's acceptance criterion.

## The pin

A contract does not let a consumer go unpinned, and a bench that freezes everything by hash must keep
recording the engine's exact version. It changes what the pin can be: with D, a dependency on a range
of versions plus the exact version recorded per run, an upgrade inside the range safe by the engine's
promise and checked by the engine's tests. The tag EX-40 asks for is the step before.

## Where the contracts live

A suggestion was to keep the contracts as documents of their own, synchronized with the desk on every
change. Two constraints shape it:

- The desk is not a source of truth (desk rule 1), and a copy kept in step in two places breaks one
  fact in one place (`documentation-rules.md` §3). So the contract lives in this repository, in a
  place of its own — a new slot of the document map, which is a decision of the ADR.
- The synchronization is a notification, not a copy: a change of a contract produces a letter of kind
  `notice` to each consumer whose scenario declares the changed surface, one letter per addressee
  (desk rule 8), naming the document and the commit.

## Open questions

1. T1 and T2 first, T3 later, or all three in one ADR?
2. Schemas as files in the repository, generated from the code, or the code generated from them?
3. Does a consumer's declaration stay in its scenario, or does each contract document carry a "used
   by" list — which would be a second place for the same fact?
4. Whether `ADRs exercised` of a scenario keeps naming ADRs, or names contract documents once they
   exist.
5. Whether the reconciliation POC, the one consumer with a second contributor, joins the desk (the
   owner intends to do it from that project), so that its requests reach the engine by the same path.
