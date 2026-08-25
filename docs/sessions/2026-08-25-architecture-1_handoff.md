# Session 2026-08-25-architecture-1

## Type
architecture

## Goal
After the freeze of ADR 014 and ADR 021, audit the documentation for remaining open questions,
contradictions and ADR-rule violations, and close the documentation debts the audit finds.

## Completion criteria
- The freeze-gate obligations of ADR 014 and ADR 021 are checked against the delivered documents.
- Every inconsistency found is either fixed in this session or recorded as a next step with an owner.
- The open questions left by the two ADRs and their implementation sessions are mapped in one place.

## Scope boundaries
- No code changes.
- No roadmap reorder and no execution of the notes triage (roadmap step 13).
- No new ADR and no change to any frozen decision; fixes stay editorial (status labels and links).

## Status
`completed`

## Result
The audit found the freeze gates of ADR 014 and ADR 021 fully satisfied: branches merged, overview,
`README.md` and the walkthrough updated in the same merge, class 4 evidence in place, registries
truthful, scenario and walkthrough ADR lists consistent in both directions. Two documentation debts
were found and fixed:

1. ADR 021 was missing from the dependencies of ADR 014 — in the ADR's `Related ADRs` and in the
   registry's `Depends on` column — although the frozen §4 lands the call audit in the ADR 021
   record channel. The 2026-08-24 amendment that moved the audit into the record channel did not
   extend the list. Fixed as an editorial links fix, recorded in the ADR change log.
2. Five open notes still described ADR 014 (and one of them ADR 021) as `Draft` in their `Affected`
   headers. The status mentions were refreshed; the recovery note now records that its retry-policy
   item (b) is unblocked by the delivered error classes.

## Decisions
No architectural decision was made; all changes are editorial. The notes triage stays roadmap
step 13 and was deliberately not executed here.

## Open questions
The map of what remains open after ADR 014 and ADR 021, gathered by the audit:

- From ADR 014 Leaves open: retry/backoff (recovery note (b), now unblocked); token or cost budgets;
  `pre_functions`/`post_functions`; `prompt_ref` (measured by the hand-build of `load-test-triage`);
  the adapter package's protocol set and productization; run-time model selection (`model` is a
  literal today); the instruction-formatting module; the template-file channel for `ask` fields.
- From ADR 021 Leaves open: retention of `records.jsonl` beyond the session; a schema version
  marker; a rollback marker. The `llm` details member is closed by ADR 014 §4.
- Unowned from the implementation sessions: the action-registry twin of the provider-registry bug
  (`get_registered_actions_info` returns the registry dictionary itself); the adapter roughnesses
  (overflow classified by an error-body substring, `load_config` in node call options refused by the
  chat call rather than at build, the model listing reporting the window of instances the adapter
  did not load); definition inclusion for the duplicated walk nodes (a `workflow-authoring`
  question).

## Next steps
1. Roadmap step 9: atomic state write and a session lock, one `fix/` session without an ADR.
2. Roadmap step 10: build `load-test-triage` by hand on prepared data — the phase consumer of
   ADR 014 and the measurement of the answer-shape, function-inventory and authoring gaps.
3. Decide the action-registry twin: its own `fix/` branch or folded into the next session that
   touches the registries (roadmap step 12 is a candidate).
4. Roadmap step 13, the notes triage, now also carries the periodic staleness check this session
   performed by hand.

## References
- Branch: `development`.
- ADRs: ADR 014, ADR 021 (editorial links and status-label fixes only).
- Changed documents: `docs/adr/adr-014-llm-node-and-provider-adapter.md`, `docs/adr/README.md`,
  and the `Affected` headers of five notes in `docs/architecture/notes/`.
