# Session note

## Type
architecture

## Goal
Work ADR 014 (LLM node and provider adapter) from Draft: re-baseline the draft against the ADRs
accepted since it was written (015, 016, 017, 018), settle its six open points in critical mode,
and decide the transition — POC or Implementing.

## Completion criteria
1. Each of the six open points at the end of the ADR 014 Decision section is answered or explicitly
   deferred, with alternatives and costs stated.
2. The ADR 014 text reflects the settled decision (edited in place on `development`, as the process
   allows for a Draft) and its change log records the session.
3. The transition out of Draft is decided and, if taken, reflected in the registry row; if a POC is
   chosen, its question is stated in the ADR.
4. Open notes intersecting ADR 014 have their `Affected`/`Status` reconciled where the discussion
   touches them.
5. This session note is completed and committed.

## Scope boundaries
- No implementation and no POC code in this session: code work starts only in the branch the decided
  transition creates.
- Retry/backoff policy stays out: recovery note (b) remains the next ADR after 014 and only its
  error-class interface is decided here.
- Token/cost budgets (ADR 010 neighbourhood) stay out of scope, as the draft already states.
- The uncommitted sharpening of `2026-08-18-adr012-deferred-questions.md` predates this session and
  is handled as its own commit, not folded into this session's changes.

## Status

## Result

## Decisions

## Open questions

## Next steps

## References
- Branch: `development` (Draft ADR per `docs/adr/process.md` git linkage)
- Subject: `docs/adr/adr-014-llm-node-and-provider-adapter.md`
- Previous session: `2026-08-21-implementation-1_handoff.md`
