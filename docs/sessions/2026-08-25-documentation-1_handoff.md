# Session note: 2026-08-25 documentation 1

## Type
`documentation`

## Goal
Carry the documentation that six implementation sessions of ADR 014 made inaccurate, merge
`feature/adr_014-llm-node-and-provider-adapter` into `development`, and take ADR 014 through its
freeze gate.

This is the closing session of the ADR 014 arc, the second half of session 4 as sized in
`2026-08-24-investigation-1` and split when `2026-08-25-implementation-3` was opened.

## Completion criteria
- `README.md` states what an operator now sees: a model step exists, a provider is configured
  rather than coded, a call can fail in named classes, and a call leaves an account behind.
- `docs/architecture/overview.md` describes the delivered architecture of the model call — the
  action, the registered adapter, the seat and its finalization, the configuration block, the error
  classes and the audit — as it is, without repeating the rationale of the ADR.
- `examples/README.md` and the walkthrough of `folder-inventory-to-csv` carry the three variants:
  one walkthrough with one class 4 header, a section per variant, and what the operator has to
  configure before any of them runs.
- The scenario registry row of `folder-inventory-to-csv` names ADR 014 and the variants.
- The session registry carries a row per session of this branch, added on `development` at the merge.
- ADR 014 is `Accepted` in its own Status field and in the ADR registry, with its active branch
  cleared, and every condition of the freeze gate in `docs/adr/process.md` is met and stated.
- `uv run pytest` and `uv run ruff check .` run clean from the command line before the merge.

## Scope boundaries
- No code change. A defect found while writing is recorded as a finding, not fixed here.
- No new scenario document: the three variants are named variants of one class 4 scenario, by the
  variants rule of `docs/architecture/scenarios/README.md`.
- No measurements in committed documentation: what the by-hand runs measured is machine-specific and
  stays in the notes of the sessions that measured it (documentation rule 8).
- No work on the open questions the branch carries: they are handed to the next steps.

## Status
`completed`

## Result
The documentation set is written; the branch then merges into `development`, where the registries,
the roadmap and the ADR status field live, and ADR 014 is frozen there.

- `README.md` gains "Calling a model": what an `llm` node declares, how a prompt resolves, how the
  two reply formats are read, the `providers` section with its five keys and the rule that a sixth
  is refused at load, the three adapters and where each lives, the nine error codes a transition can
  route, and what a call leaves behind in the record stream and in artifacts. The configuration table
  gains its `providers` row, and the examples table names the three variants.
- `docs/architecture/overview.md` gains "Model call": the action, the adapter contract with its two
  operations, the seat and why it is module state, the configuration block and its non-snapshotting,
  the six classes plus the action's three, and the audit. `PROVIDER_REGISTRY` joins the registry
  table, `providers` joins the help contract type keys, and the `details` member of a node record is
  named as the action's rather than the engine's.
- `examples/folder-inventory-to-csv.md` carries the three variants under one class 4 header: what
  each adds to the base walk node by node, what it delivers, the failure codes it adds, and the
  one line an operator edits before `tiered` runs anywhere. `examples/README.md` lists the variants
  and points at that one walkthrough. The header's `ADRs exercised` gains ADR 014.
- The scenario registry row of `folder-inventory-to-csv` names ADR 014 and says the example ships in
  three named variants. Seven session rows were added: the six of this branch and this one.
- ADR 014 is `Accepted`, its active branch cleared in the ADR file and in the registry, whose summary
  now says the audit is carried by the record channel rather than by events. Roadmap step 8 is done.

Verification: `uv run pytest` 758 passed and `uv run ruff check .` clean, both run before the merge.
No code changed in this session, so the numbers are the ones the preceding session left. The record
line quoted in `README.md` was taken from a real run of the `described` variant on the `fake` adapter
rather than written by hand; its token counts are the only illustrative part.

**The freeze gate** of `docs/adr/process.md`, condition by condition:

- The feature branch is merged into `development`.
- The tests pass, end to end included: the three variants run through the installed CLI.
- Context, Decision and Consequences describe the delivered result; six change-log entries record
  every departure the implementation made from what the Draft imagined.
- `docs/architecture/overview.md` describes the delivered architecture, updated in the same merge.
- The consumer named in `Consumer` can act from the delivered surface, shown by a class 4 scenario
  that lists the ADR: the three variants of `folder-inventory-to-csv`, covered by tests on the `fake`
  adapter and run by hand against a local model server in `2026-08-25-implementation-3`.
- No POC code reached `development`: this ADR had no POC.

## Decisions
1. **One walkthrough carries the three variants, not one walkthrough each.** The alternative was a
   file per variant with a header of its own, which reads closer to the promise of `examples/README.md`
   that every template has a walkthrough beside it. It was rejected because a class 4 header *is* a
   scenario: four headers are four scenario identifiers and four registry rows for what the variants
   rule of `docs/architecture/scenarios/README.md` calls one example with named variants, and the
   preceding session had already ruled out a second scenario document. The cost is a walkthrough that
   is now long enough to need its own table of variants at the top of the section.
2. **The model call is documented in `README.md` as a surface of its own, not inside "Writing a
   custom function".** A reader looking for the fifth registration kind will find it beside the other
   four, which was the alternative, but the operator question is not "how do I register an adapter" —
   it is "what do I put in the configuration file so this definition runs here". The section is
   ordered for that question, and the registration kinds keep one sentence naming `@register_provider`.
3. **What the by-hand runs measured stays out of the repository.** Durations, token counts and model
   identifiers are true of one machine on one day (documentation rule 8), so the walkthrough states
   behaviour and the numbers stay in `2026-08-25-implementation-3`. The one exception is the
   illustrative `usage` in the `README.md` record line, which names no model of anyone's machine.

## Open questions
Carried unchanged from `2026-08-25-implementation-3`, none of them owned by this session:

- A node's `model` is a literal, so a definition that chooses a model per node pins itself to one
  installation. Whether `model` should resolve a reference belongs to the ADR that owns the node
  contract. The `tiered` variant pays for it with the one line an operator has to edit.
- The three variants duplicate the eleven nodes of the described walk. Whether a definition should be
  able to include another is a question for the `workflow-authoring` scenario.
- The overflow class is told apart by a substring of an error body; a `load_config` written into a
  node's call options is refused by the chat call rather than at build time; the model listing reports
  the window of instances the adapter did not load.
- The action-registry twin of the provider-registry bug, carried from `2026-08-24-implementation-5`
  and still unowned.

## Next steps
1. Roadmap step 9: atomic state write and a session lock, one `fix/` session without an ADR.
2. Decide the action-registry twin: a `fix/` branch of its own, or fold it into the session that
   next touches the registries.
3. Roadmap step 10: build the exit scenario `load-test-triage` by hand on prepared data. It is the
   phase consumer of ADR 014 and the first real use of the surface this branch delivered, and it
   measures the answer-shape and function-inventory gaps and the lower bound of the authoring need.

## References
- Branch: `feature/adr_014-llm-node-and-provider-adapter`, merged into `development` and deleted.
- Documents changed: `README.md`, `docs/architecture/overview.md`, `examples/README.md`,
  `examples/folder-inventory-to-csv.md`, `docs/adr/adr-014-llm-node-and-provider-adapter.md`,
  `docs/adr/README.md`, `docs/architecture/scenarios/README.md`, `docs/architecture/roadmap.md`,
  `docs/sessions/README.md`.
- Preceding note: `2026-08-25-implementation-3_handoff.md`; the branch's other notes are
  `2026-08-24-implementation-3` to `-5` and `2026-08-25-implementation-1` and `-2`.
- Related ADRs: ADR 014, frozen by this session.
