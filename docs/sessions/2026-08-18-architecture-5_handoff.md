# Session note

## Type
architecture

## Goal
Determine everything still required to close phase 1 against the criterion "the engine core is
usable in different user scenarios", and decide the workflow input mechanism, opening it as a
Draft ADR.

## Completion criteria
1. The phase 1 completion gate is recorded as an explicit list of remaining work items.
2. The input-mechanism direction is decided (workflow as reusable definition vs single-run object
   with a template entity) with alternatives and trade-offs stated.
3. ADR 012 is opened as Draft with its registry row.

## Scope boundaries
- Architecture and documentation only; no runtime implementation changes.
- ADR 012 stays in Draft; moving it to Implementing is a follow-up decision.

## Status
completed

## Result
Phase 1 readiness was assessed against the project's own definition (2026-08-09 scope: ADR 007-009
mandatory, 010 optional — all Accepted, plus ADR 011) and against the stricter user criterion. The
formal scope is complete; the gap to "usable in different user scenarios" is the inability to
parameterize a run without hand-editing workflow JSON, plus onboarding and minor-defect debt.

The `resume` operator-output flags were analyzed: they fabricate the paused node's output (the
interactive-answer mechanism deferred to phase 2 by ADR 007 §4), are absent from the frozen
contract, and are broken (`WriteParamMode` by-value construction against by-name parser choices).
They are not a parameter-input path and will be removed from the v1 surface under ADR 012.

ADR 012 "Workflow input parameters" was opened as Draft: a declared `inputs` block (mirror of
`deliverables`), a typed multi-parameter `set-input` command valid only before the first node
visit, codec-typed values (raw string or JSON decoded via registered codec type names), a one-shot
assignment option on `run`, setup-time enforcement of required inputs, and removal of the
uncontracted `resume` flags.

## Decisions
1. Stance chosen for ADR 012: a workflow file is a reusable definition; run-specific values bind
   to the session at creation time. The alternative (single-run workflow plus a separate template
   entity, input via interactive action) was rejected for phase 1: it makes parameterized
   non-interactive runs impossible by design and requires a speculative template subsystem. The
   interactive input action remains the complementary phase-2 mechanism for mid-run input.
2. Two-step binding uses a dedicated `set-input` command (multiple typed parameters per
   invocation) rather than flags on `init-new-session`; `run` additionally carries the one-shot
   assignment form.
3. Input values are typed through the existing codec registry (name, value, codec type name), so a
   bound input round-trips exactly like any session parameter (ADR 006).
4. Phase 1 completion gate (in order):
   1. ADR 012 implemented and Accepted (includes removing the broken `resume` flags).
   2. Minor-defect session: UTF-8 BOM rejection in config/workflow loading, `init-new-session`
      top-level `session_id: null`, blank lines in the prettytable CSV on Windows; decide the
      default of `hard_max_nodes_visited` (1000 is low for real folder scans).
   3. Documentation session: installation and usage documentation (quick start, template how-to
      with `set-input`/`--export-dir`), portable `simple_workflow.json` (or fixture moved into
      `tests/`).
   4. Release: merge `development` into `main`, tag the first version.

## Open questions
1. Exact assignment syntax for `set-input`/`run` (argparse shape for repeatable name/type/value
   with values containing `=` and spaces) — settled when ADR 012 moves to Implementing.
2. Whether the minor-defect session also raises the default hard cap or only documents it.

## Next steps
1. Review the ADR 012 Draft, refine the assignment syntax, and move it to Implementing on
   `feature/adr_012-workflow-input-parameters`.
2. Run the minor-defect fix session (gate item 2).
3. Run the documentation session (gate item 3).
4. Release phase 1 (gate item 4).

## References
- ADR: `docs/adr/adr-012-workflow-input-parameters.md`
- Phase 1 scope definition: `2026-08-09-architecture-2_handoff.md`
- Operator findings: `2026-08-18-investigation-1_handoff.md`
- Resume-flag analysis precedent: `2026-08-18-implementation-5_handoff.md`
- Branch: `development`
