# Session note: 2026-08-24 architecture 3

## Type
`architecture`

## Goal
Open Draft ADR 021, the node-record channel, deciding the destination of a node record against the
four alternatives and the consumer against decision 4 of `2026-08-24-investigation-1`.

## Completion criteria
- ADR 021 exists as Draft on `development`, with its registry row.
- The destination is decided against the four alternatives of the investigation note: the session
  journal, a record list inside the state, an append-only file outside the state, artifacts under
  ADR 011.
- The ADR states how the record stream meets the bounded read surface of ADR 018.
- The `Consumer` section names either the ADR 014 gate variants or the ADR's own class 2 or class 4
  evidence, so the decision is freezable.
- The relation to roadmap step 9 (atomic state write, session lock) is stated: one concern or two.

## Scope boundaries
- No code is changed and no implementation branch is opened.
- ADR 014 stays `Draft` and its body is untouched; its §4 is read, not rewritten.
- Roadmap step 8 is not rewritten again; only ADR 021's existence is reflected where the rules
  demand it.

## Status
`completed`

## Result
Draft ADR 021, "The node-record channel", written on `development` with its registry row. The
session opened with a question the investigation note had not asked — what is recorded at all —
and settled it before the destination: the corpus already required recording (the purpose's
"explained by the journal", ADR 014 §4, the ADR 013 §9 names-not-values rule), but the general
per-visit record was undecided. All completion criteria are met; the ADR carries no open points
and is ready to enter Implementing.

Rule 11 executed in the same session: `folder-inventory-to-csv` (walkthrough header and scenario
registry row) and `load-test-triage` (header and row) list ADR 021. Rule 12 executed: the
recovery-and-resilience note's `Affected` gains ADR 021 for the append-only trail its rollback
sketch (d) assumes.

## Decisions
1. **Scope: every node visit leaves a record, engine-written, unconditional** (ADR 021 §1). The
   record carries names and codec names, never values; a `details` member per action kind is the
   seat the ADR 014 call audit will fill. Rejected in the ADR as alternatives D–F: opt-in via
   wrapping or subclassing (extension travels through registration; an action cannot write the
   trail; explainability is the engine's promise), a per-component configuration switch (the trail
   becomes an installation's habit; verbosity belongs to the definition), and the standard
   `logging` framework (a machine-configured diagnostic stream with no machine-readable consumer
   is not this channel).
2. **Destination: an append-only per-session stream outside the state**, with artifacts kept as
   the payload channel (ADR 021 §2–3) — alternative C of the investigation note, with D in its
   ADR 014 §4 role. The criterion fixed in the ADR: the state holds what a resume needs, the trail
   holds what an explanation needs. The journal (A) and an in-state list (B) are rejected for the
   state-file regime change; artifacts as the record channel (C of the note, alternative C of the
   ADR) for turning the deliverable registry into a log.
3. **Read surface: a dedicated `show-records` command in the ADR 018 §3 discipline** (ADR 021 §4);
   `show-journal` is untouched and the journal stays lifecycle-only, so nothing is bookkept twice.
4. **Consumer: the after-the-fact reader, with the ADR's own class 4 evidence** on
   `folder-inventory-to-csv` — the queue-driven walk whose per-visit history the state slots
   overwrite today. The freeze therefore does not wait on the ADR 014 gate variants;
   `load-test-triage` stays the phase consumer.
5. **Roadmap step 9 stays a separate `fix/` concern** of the same file layer; ADR 021 makes it
   cheaper (the state file stops growing), not different. Recorded in the ADR's Consequences.

## Open questions
- The `llm` details member: defined by ADR 014 on its own branch when it lands in this channel
  (its §4 wording will be re-pointed there, not here — a Draft may not constrain a Draft).
- A rollback marker in the trail: recovery note (d), undecided, now cross-linked from both sides.

## Next steps
1. Move ADR 021 to `Implementing`, open `feature/adr_021-node-record-channel`, implement, and run
   the class 4 evidence on `folder-inventory-to-csv`; merge and freeze.
2. Then, as `2026-08-24-investigation-1` planned: ADR 014 to `Implementing`,
   `feature/adr_014-llm-node-and-provider-adapter`, four sessions on one branch — amending
   ADR 014 §4 to land the call audit in this channel is part of that work.

## References
- Branch: `development`.
- Documents changed: `docs/adr/adr-021-node-record-channel.md` (new), `docs/adr/README.md`
  (registry row), `examples/folder-inventory-to-csv.md` and
  `docs/architecture/scenarios/load-test-triage.md` (ADRs exercised),
  `docs/architecture/scenarios/README.md` (both rows),
  `docs/architecture/notes/2026-08-18-recovery-and-resilience-roadmap.md` and
  `docs/architecture/notes/README.md` (Affected), this note.
- Related ADRs: ADR 021 (opened here), ADR 014, ADR 018, ADR 011, ADR 006, ADR 013, ADR 010,
  ADR 017, ADR 003, ADR 008.
- Preceding note: `2026-08-24-investigation-1_handoff.md`.
