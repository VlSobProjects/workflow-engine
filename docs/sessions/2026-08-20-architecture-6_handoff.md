# Session note

## Type
architecture

## Goal
Decide open question 1 of the ADR-0083 coverage note: whether the surfacing and the accumulating
post function belong in the core, so the node-folding half of the scenario rewrite is unblocked.

## Completion criteria
1. The question is decided in critical mode: at least two alternatives weighed, trade-offs and cost
   named, and a verdict recorded with its reason.
2. The decision states its shape: whether it needs an ADR of its own or is component work under the
   delivered ADR 015, with the precedent named.
3. Item 5 of "What is still missing" in
   `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` records the verdict instead of
   deliberately not making it, and the notes registry row carries the new state.
4. The work the decision implies is registered as next sessions, not done here.

## Scope boundaries
- No code change: no function is written, no node is folded, no test is touched. The implementation
  the verdict unblocks is its own session.
- No change to any accepted ADR beyond editorial links, and no reopening of ADR 015's frozen text.
- Frictions 2 (in-graph budget checkpoint) and 3 (script-running function for `S`) are not touched.

## Status
completed

## Result
The question is decided: the surfacing and the accumulating post function go into the core, as
component work under the delivered ADR 015 and without an ADR of their own. Item 5 of "What is still
missing" in the coverage note records the verdict with its grounds, and the notes registry row
carries the new state. The note stays `open` — frictions 2 and 3 remain. No code was written; the
fold this unblocks is registered as the next implementation session.

Verification: prose only. No code, test or example changed, so neither pytest nor ruff was run.

## Decisions
1. **The pair goes into the core.** Three alternatives weighed: core pair, external module first,
   keep the nodes. Decisive against external-first: the argument assumed an outside that would ripen
   the contract, and there is none — the only consumers live in this repository, and the
   proving-outside role is already played by the test functions of
   `tests/test_adr015_post_function.py`, written in the external shape and exercised end to end
   through the CLI. Decisive against keeping the nodes: the scenario is the yardstick for what the
   shipped core alone can carry, and ADR 015 was accepted precisely because the extra nodes are paid
   for on every interactive flow. Cost accepted knowingly: the first core components whose contract
   is the injected answer set the signature precedent, and their semantics are chosen against one
   flow's evidence; the retraction cost is low while the project is unpublished.
2. **No new ADR.** Adding registered functions changes no contract and is additive; the precedent is
   `append_to_param` and `is_collection_size_at_least`, added in session
   `2026-08-19-implementation-15` without one. ADR 015's "the branch ships the mechanism, not a
   library of functions for it" describes what that branch shipped, not a prohibition. The verdict
   lives in the coverage note; names and exact signatures are the implementation session's to choose.

## Open questions
None new. Frictions 2 (in-graph budget checkpoint) and 3 (script-running function for `S`) stay open
in the coverage note, untouched by this session.

## Next steps
1. Implementation session: add the surfacing and the accumulating post function to the core and fold
   the four data-only nodes of `tests/test_adr0083_scenario.py` (`CHECK_ROOT`, `CHECK_ISSUES`,
   `FQ_CHECK`, `FQ_COLLECT`), confirming or refuting the eleven-to-seven prediction. The same fold
   rewrites the ADR 017 case: with the check inside `ASK_ROOT`, a rejected path re-asks as an attempt
   and `max_attempts` becomes the bound there.
2. ADR 014 as its turn comes, quoting the `text_interpolation` module for its open point 1.
3. Friction 3, the script-running function for `S`, as an external module.

## References
- Branch: `development`
- Changed: `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`,
  `docs/architecture/notes/README.md`
- Decides for: ADR 015 (component work under it; the ADR text is untouched)
- Previous session: `2026-08-20-implementation-4_handoff.md`
