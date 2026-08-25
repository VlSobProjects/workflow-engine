# Session note: 2026-08-25 implementation 7

## Type
`implementation`

## Goal
Pay the code debts listed by the 2026-08-23 code audit (`2026-08-23-architecture-1` §6 item 7) in one
`refactor/` session, without changing any behaviour and without touching anything beyond that list.

## Completion criteria
- The dead code of the list is gone: `def_errors`, `SubmitStatus`, `SubmitResult`,
  `PresentResponse.submit`, `PresentResponse.expected_input`, `renderers/simple_render.py`, the empty
  `runtime/` and `parsers/` packages.
- The misspelled identifiers of the list are corrected: `storage_fatcory`, `_get_commend`,
  `_factory_sate_stub`, `intend`.
- The duplicated tail of `run_workflow`/`resume_workflow` is written once.
- `CommandResult.from_state`/`from_state_full` are one method.
- The five `parameter_from_dict` variants share one implementation.
- `_start_engine` is decomposed so that its loop is readable in one pass.
- `uv run ruff check .` clean and `uv run pytest` green, with the same number of passing tests as the
  baseline of this session (808) unless a test was deliberately removed with its dead subject.

## Scope boundaries
- Only the debts named by `2026-08-23-architecture-1` §6 item 7. No other cleanup, no new feature,
  no new test beyond what a removal or a rename forces.
- No behaviour change: every published surface — the command contract, the question block, the state
  and record files — keeps the shape it has.
- The notes triage (roadmap step 12) is not touched.

## Status
`completed`

## Result
Every debt of the list is paid and nothing outside it was touched. `ruff check` clean,
`ruff format --check` clean, 808 tests pass — the same 808 as the baseline taken before the first
edit, so no test was lost and none was added.

- Dead code removed: `def_errors`, `SubmitStatus`, `SubmitResult`, the `submit` and `expected_input`
  fields of `PresentResponse`, `renderers/simple_render.py` with its now-empty package, and the
  `runtime/` and `parsers/` packages, which held nothing but an empty `__init__.py`.
- Misspellings corrected: the module `bootstrap/storage_fatcory.py` is `storage_factory.py`,
  `_get_commend` is `_get_command`, `_factory_sate_stub` is `_factory_state_stub`, and the `intend`
  parameters of the three `dict_to_text_lv*` helpers are `indent`.
- The identical eleven-line tail of `run_workflow` and `resume_workflow` is now `_run_result`.
- `CommandResult.from_state_full` is gone; `from_state` carries the `full` flag it already passed on
  to `get_data_from_state`, and `show_state` is its only caller with `full=True`.
- The `parameter_from_dict` family keeps its four public names and their signatures — 149 call sites —
  but the type check is written once, in `check_param_type`, which the other four now call.
- `_start_engine` went from 144 lines to 52. Each way out of its loop is a named function that
  journals its own event and saves the state: `_budget_exceeded_response`, `_safety_cap_response`,
  `_node_failed_response`, `_paused_at_question_response`, `_runtime_error_response`,
  `_completed_response`, beside the `_visit_cap_response` that already existed. The routing of a
  concluded node's output is `_route_output`, returning a `_Routed` record.

No documentation needed synchronizing: nothing an operator, a calling program or a shipped template
sees was changed, and `docs/architecture/overview.md` names none of the removed or renamed things.

## Decisions
1. **The `parameter_from_dict` variants keep their names.** The debt is the duplicated raise-logic,
   not the number of entry points. Collapsing the four readers into one function with a sentinel
   default would have edited 149 call sites for no gain in what any of them says; the alternative
   taken shares the check and leaves the call surface alone. `check_param_type` was made the shared
   check rather than a new private helper, because it already was that check with a public name.
2. **`_start_engine` decomposes by exit, not by phase.** Every early return in the old body was the
   same shape — journal an event, save the state, build a `PresentResponse` — so one function per
   exit removes the length without inventing a structure the loop does not have. The alternative,
   splitting the loop body into "before the action" and "after the action" halves, was rejected: the
   per-node cap check deliberately sits between them (ADR 017 §1) and the split would have hidden
   why.
3. **`_Routed` carries the output back.** An interactive node may compute on the accepted answer
   (ADR 015 §3), and it is the computed output, not the caller's, that the next action reads as its
   previous one. A helper that returned only the next node would have silently dropped that.
4. **The debt list was read as closed.** `2026-08-23-architecture-1` §5.2 also assigns the renaming
   of `test_adr0083_scenario.py` to "the `refactor/` session", but roadmap step 11 bounds this
   session by the §6 debt list, and §5.2 names the note `adr0083-scenarios-coverage` in the same
   breath. Both were left to the notes maintenance of step 12, where the note is closed anyway.

## Open questions
1. The rename of `test_adr0083_scenario.py` — the word "scenario" is now a reserved kind of document
   and a synthetic e2e test may not claim it. Decided by `2026-08-23-architecture-1` §5.2, not done
   here, no target name proposed anywhere. It belongs with the note it was named beside.

## Next steps
1. Step 12: execute the notes triage decided by `2026-08-23-architecture-1` §4, and settle the
   `test_adr0083_scenario.py` rename with the note it travels with.
2. Step 13: the live-model rehearsal of the `reorganize-folder` plan variant.

## References
- Branch: `refactor/audit-code-debts`
- Debt list: `docs/sessions/2026-08-23-architecture-1_handoff.md` §6 item 7
- Changed: `src/workflow_engine/engine.py`, `cli/use_cases.py`, `cli/contract.py`, `cli/main.py`,
  `tools.py`, `actions/action_present.py`, `actions/base_actions.py`, `bootstrap/bootstrap.py`,
  `bootstrap/storage_factory.py` (renamed), `tests/test_engine.py`; deleted `renderers/`, `runtime/`,
  `parsers/`
- ADRs: none. The removed `PresentResponse` fields are the ones ADR 013 §2 already declares replaced
  by the answer declaration.
