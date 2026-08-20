# Session note

## Type
implementation

## Goal
Implement ADR 015: an interactive node may run a registered function on an accepted answer before
that answer becomes the node output.

## Completion criteria
1. The injection convention of a registered function lives in one place and every caller uses it,
   with the guard's differing convention stated next to it (ADR 015 §3a).
2. `ask` carries optional `function_name` / `function_parameters`, and the engine runs the function
   between the state view and the transition selection, so the function's result is the output the
   guards see and the engine applies (§3, §4, §8).
3. A failing post function fails the node the way any registered function does (§5); the refusal
   rules and the answer journal are untouched (§6, §7).
4. The accessor pair on `ActionNodeOutput` ships, keeping `ParamWrite` internal and `APPEND`
   explicit (Implementation notes).
5. `uv run pytest` and `uv run ruff check .` pass, with new tests covering the behaviour.
6. `README.md` and `docs/architecture/overview.md` carry the change; the ADR body records the
   contract points settled here in its change log.

## Scope boundaries
- No pre-processing of the question: ADR 015 §1 defers it to the templating decision.
- No new core registered function: the branch ships the mechanism, and the tests register their own
  functions. The gap is recorded in the next steps.
- No visit or attempt ordinals in `interactive_answered`: that is ADR 017's implementation.
- ADR 013 is Accepted and untouched; the class hierarchy of actions stays as it is (§3a,
  alternative F).

## Status
completed

## Result
ADR 015 is implemented. An `ask` node may carry `function_name` and `function_parameters`; the engine
runs the function on an accepted answer between the state view and the transition selection, and its
result is the output of the node. All six completion criteria are met: `uv run ruff check .` is clean
and `uv run pytest` reports 384 passed, 14 of them new.

The two workarounds the ADR was opened for are gone in one node, which the test suite shows rather
than claims: a declared answer value routes its own node without a surfacing node, and one asking
node accumulates its answers and decides on "enough" itself — the shape the `CHECK`/`COLLECT` pair
used to need.

## Decisions
1. **Two contract points the Draft left implicit were settled against the code** and written into the
   ADR with a change log entry: a failure answer never reaches the function (§5) — it carries a code
   the node declared and its transitions route it, and computing there could replace a declared
   refusal with a success; and the function's result is the *whole* node output (§4), so a function
   that builds a fresh result instead of editing the one it was given drops the answered values. The
   second is the likeliest author mistake, so it is in the operator help as well.
2. **The injection convention lives in `function_injection`**, with the guard's differing convention
   beside it, and the four callers use it. That is §3a done: the fourth copy was never written and
   the difference between the two conventions is now readable in one place.
3. **The stage is a method of the interactive action, not a special case in the engine.**
   `BaseInteractiveAction.process_answer` holds the contract (a failure answer returned untouched,
   artifact errors turned into an error output) and `_process_answer` is what an action overrides;
   the engine calls it at the one place an answer arrives. `AskAction` composes a registered function
   the way `StopAction` does, and the hierarchy is untouched (alternative F).
4. **The accessor pair shipped** as `ActionNodeOutput.get_param` / `set_param`. `get_param` carries
   the name the read-only state view already uses, so a function reads a pending value and a stored
   one the same way; `set_param` writes `SET` only and overwrites by default, because a question
   asked again in a loop answers the same names. `APPEND` stays spelled out in `param_writes`.
5. **No core function was added.** The branch ships the mechanism; the test functions are test-only
   and say so. The gap is real and named in the next steps.

## Open questions
None from the implementation itself. Two facts about neighbouring documents are recorded rather than
fixed here, both deliberately out of this branch's scope:
- The ADR-0083 coverage note still says ADR 015 is `Draft` and still counts the `echo_value` friction
  and the missing appending function as open. It is the yardstick of phase 2 and deserves a real
  re-measurement against the delivered stage, not a one-line status edit.
- No core registered function can consume a pending answer, so the payoff is available only to
  whoever writes a function.

## Next steps
1. Merge into `development` and set ADR 015 to `Accepted` through the freeze gate; ADR 017 then has
   the single Implementing slot free (rule 11).
2. Re-measure `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` against the
   delivered stage: what the post function removes from its node count, its `Affected` line, and
   whether the "one function to write" gap should become a core function of its own.
3. ADR 016 and ADR 017 as their turns come; 016 has two small open points to settle at or before
   implementation, 017 has none.

## References
- Branch: `feature/adr_015-computation-inside-an-interactive-node`
- ADR: `docs/adr/adr-015-computation-inside-an-interactive-node.md`
- Added: `src/workflow_engine/function_injection.py`, `tests/test_adr015_post_function.py`
- Changed: `src/workflow_engine/actions/action_ask.py`, `actions/base_actions.py`,
  `actions/action_nodes.py`, `transition/guards.py`, `engine.py`, `output.py`,
  `help_contract/models.py`, `README.md`, `docs/architecture/overview.md`
- Previous session: `2026-08-20-architecture-4_handoff.md`
