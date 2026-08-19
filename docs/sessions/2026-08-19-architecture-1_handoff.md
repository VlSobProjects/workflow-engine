# Session note

## Type
architecture

## Goal
Close phase 1 formally, set the scope and order of phase 2, and open the first two phase 2 decisions
as Draft ADRs.

## Completion criteria
1. The relation between the `v0.1.0` tag and further architecture work is decided and recorded.
2. The phase 2 goals are stated with the architectural constraint they run under.
3. The open architecture notes are triaged against phase 2: each is either tied to a draft ADR
   through its `Affected` field or explicitly left open with a reason.
4. ADR 013 and ADR 014 are opened as Draft with their registry rows.

## Scope boundaries
- Architecture and documentation only; no runtime code changes.
- Both ADRs stay in Draft; moving either to POC or Implementing is a follow-up decision.
- No further ADRs are opened in this session; retry/backoff and workflow-definition introspection
  stay notes until ADR 013 is in Implementing.
- Release and distribution questions are not touched.

## Status
completed

## Result
Phase 1 is closed by the existing `v0.1.0` tag on `main`. Phase 2 has two goals — LLM calls as
workflow nodes, and an interactive node whose other end may be an AI agent or an operator — and one
constraint: it is additive to the phase 1 model. ADR 013 (interactive exchange and typed answer
contract) and ADR 014 (LLM node and provider adapter) were opened as Draft. Three notes had their
`Affected` field extended to the new drafts; the others stay open unchanged.

## Decisions
1. **No second line for phase 1.** The `v0.1.0` tag is the phase 1 artefact. A fix may still be
   applied to it from a branch cut off the tag if ever needed, but no ADR and no architecture
   discussion targets that version; everything lands on `development`. The alternative — a living
   maintenance branch receiving backports of "phase 1 compatible" ADRs — was rejected: it doubles
   merges and documentation, conflicts with the rule that registries are edited only on
   `development`, and exists only to hedge against phase 2 being invasive, which is handled by the
   next decision instead.
2. **Phase 2 is additive.** LLM nodes and the interactive node are new components (actions, a
   registration kind, CLI options) and do not change the semantics of existing nodes, guards,
   transitions or the bus. Should a phase 2 ADR find this impossible, that ADR records it, and that
   is the moment a branch off `v0.1.0` becomes justified — not before.
3. **One answer contract, two sources.** The interactive node (ADR 013) and the LLM node (ADR 014)
   both receive "an answer from the other end" and bind it to typed parameters. The declaration of
   the expected answer is designed once, in ADR 013, in the shape of the ADR 012 `inputs` block, and
   ADR 014 reuses it. Designing the two separately was named the main architectural risk of phase 2.
4. **Vendor code stays outside the core.** ADR 014 gives the core a provider-neutral LLM action and
   an adapter contract; concrete providers are external modules (ADR 005). The rejected extremes
   were "no core change, LLM is a plain function" (verbose authoring, parsing and audit duplicated
   per vendor) and "vendor clients inside the core" (dependencies and provider churn in the engine).
5. **Order of phase 2 work** under rule 11 (one ADR in POC/Implementing at a time): ADR 013 first,
   because it carries the largest architectural risk and tests the additivity constraint; ADR 014
   second; retry/backoff by error class and workflow-definition introspection afterwards, each as
   its own ADR when its turn comes. LLM provider work may proceed as a `poc/` external module without
   an ADR as long as it needs no core change.
6. **Notes triage.** Recovery roadmap: (a) is carried by ADR 013, (b) remains the next ADR after
   014, (c) atomic `state.json` write is a small `fix/` task without an ADR, (d)/(e) stay after
   phase 2. ADR 012 deferred questions: §1 shallow resolution is decided inside ADR 014 (prompt
   templates), §3 definition introspection waits for its own ADR, §2 codec aliases stays hardening.
   `save_as` gets `Affected: ADR 013` because author-chosen parameter naming reappears there. Hard
   node cap, entry-point discovery and installation/distribution stay open and untouched.

## Open questions
- Whether `describe-workflow` (ADR 012 deferred §3) must precede ADR 013 Implementing for an agent
  that drives the engine, or can follow it. Decide when ADR 013 leaves Draft.
- Whether the LLM action's answer parsing and the interactive answer decoding share one code path
  or only one declaration shape. Decide in ADR 014 once ADR 013 is settled.

## Next steps
1. Refine ADR 013 in Draft: settle the answer-submission transport (`resume --answer` form), the
   escalation semantics and the pause-vs-fail boundary; then move it to POC or Implementing.
2. Refine ADR 014 in Draft after ADR 013's answer declaration is settled.
3. Open the small `fix/` task for the atomic `state.json` write.
4. After ADR 013 reaches Implementing: open the retry/backoff ADR (recovery note (b)) and the
   workflow-definition introspection ADR (ADR 012 deferred §3).

## References
- ADRs opened: `docs/adr/adr-013-interactive-exchange-contract.md`,
  `docs/adr/adr-014-llm-node-and-provider-adapter.md`
- Notes touched: `docs/architecture/notes/2026-08-18-recovery-and-resilience-roadmap.md`,
  `docs/architecture/notes/2026-08-18-adr012-deferred-questions.md`,
  `docs/architecture/notes/2026-08-19-node-save-as-redundancy.md`
- Phase 1 tag: `v0.1.0` on `main`
- Phase 1 gate definition: `2026-08-18-architecture-5_handoff.md`
- Branch: `development`