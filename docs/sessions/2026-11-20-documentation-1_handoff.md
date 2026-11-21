# Session 2026-11-20-documentation-1

## Type
`documentation`

## Goal
Write the class 2 scenario `model-call-reading` — the use of the engine by the `llm-test-bench`
project — as the answer EX-40 (2026-11-20, the engine keeps a scenario of the bench's use) to the desk
letter EX-37 (2026-11-18, llm-test-bench joins the desk) promises, and capture as architecture notes
the contract questions the discussion of it raised.

## Completion criteria
- `docs/architecture/scenarios/model-call-reading.md` exists with the full template header, the
  reading and the recount, the surfaces of the engine the bench takes with where each is described and
  whether it is a contract or an implementation detail, the expected paths and the open decisions.
- Every statement about a surface is checked against `README.md`, the overview or the code, not
  recalled.
- `ADRs exercised` lists the decisions the bench named in EX-37.
- Two architecture notes in `docs/architecture/notes/`: the published contract of the engine and how a
  consumer asks for a change to it; the read contract every storage backend implements.
- The branch is merged into `development`; the scenarios, notes and sessions registries carry their
  rows; `What it changed` of EX-37 names the scenario and the commit.

## Scope boundaries
- No code, no ADR, no roadmap change. The contract and the storage read contract are decided in
  architecture sessions, not here.
- No letter is released. A draft to `llm-test-bench` about the session's copy of the definition is
  written only after the merge, as a `draft`.
- The documents of `llm-test-bench` and of the reconciliation POC are not touched.

## Status
`completed`

## Result
- `docs/architecture/scenarios/model-call-reading.md`: the class 2 scenario of the bench's use — one
  reading of its example task over a one-node `llm` definition under the `fake` adapter, then a
  recount with no session — with the fifteen surfaces it takes, each with where it is described, its
  ADR and whether it is a contract, six expected paths and six open decisions.
- Every surface was checked against `README.md`, the overview and the code. The session's copy of the
  definition was found to be an implementation detail: `JsonStorage` writes it as its serialization of
  the parsed definition, not as a copy of the file passed, and a database backend will not have it.
- Note `2026-11-21-published-contract-and-consumer-requests`: the engine writes the contract, a
  consumer asks for a change by a request letter, three levels (command line, definition format,
  component API), four ways to check it, the pin, and where contracts live.
- Note `2026-11-21-storage-read-contract`: the facts about a session every storage backend gives a
  read-only reader, the gaps today, and three ways to serve them.

## Decisions
- `ADRs exercised` lists the eight ADRs the bench named, as EX-40 promised; ADR 003, 004 and 008 are
  not added, because naming the storage layout would sanction a dependency the bench must not have.
  ADR 002 and ADR 016 wait for the bench's confirmation (open decision 6 of the scenario).
- The contract is the engine's: a consumer declares what it uses in its scenario and asks for more by
  a request letter, which the engine implements or refuses with the reason.
- `Storage` as a class stays internal. What is published is a read contract of facts and formats every
  backend must give, served read-only; the writes stay with the engine.
- Contracts live in this repository; the desk is told of a change by a `notice` to each consumer that
  declares the changed surface, never kept as a synchronized copy (desk rule 1).

## Open questions
- Whether the contract comes as one ADR or one per level, and whether it precedes the database backend
  as its acceptance criterion; both are in the contract note.

## Next steps
1. After the merge, a `draft` letter to `llm-test-bench` in answer to EX-40's promise: the scenario is
   written; `workflow.json` is not a surface, and the bench's own definition file is its evidence;
   whether it relies on ADR 002 and ADR 016.
2. Fill `What it changed` of EX-37 with the scenario and the merge commit.
3. The owner connects the reconciliation POC to the desk from that project.
4. An architecture session triages the two notes and decides whether the contract ADR opens before the
   provider-facts ADR of EX-38, checking the registry against general rule 11.

## References
- Branch: `docs/model-call-reading-scenario`
- Changed: `docs/architecture/scenarios/model-call-reading.md` (new),
  `docs/architecture/notes/2026-11-21-published-contract-and-consumer-requests.md` (new),
  `docs/architecture/notes/2026-11-21-storage-read-contract.md` (new), this note
- Desk letters: EX-37 (2026-11-18, llm-test-bench joins the desk), EX-38 (2026-11-19, the environment a
  model call ran in), EX-39 (2026-11-19, the value written at every visit of a node), EX-40
  (2026-11-20, the engine keeps a scenario of the bench's use)
