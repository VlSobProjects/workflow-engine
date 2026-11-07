# Session 2026-11-07-implementation-1

## Type
`implementation`

## Goal
State, wherever the node key `max_attempts` is described, that it counts the retries after the first
run of the node and not the runs, and what its default gives, as the `payment-reconciliation` project
asked; the behaviour is not changed.

## Completion criteria
- The transition hints of `llm` and `ask` state that `max_attempts` counts the retries after the first
  call or question and that the default `3` allows four.
- `README.md` and `docs/architecture/overview.md` state the same: N allows N + 1 runs in one visit.
- `examples/approve-and-copy.md` no longer calls `max_attempts` 2 "two attempts"; it states three
  questions in all.
- A test pins the count for an `attempts` transition towards another node: N retries, then the route.
- `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- No change of behaviour and no new ADR; the key is not renamed and accepted ADRs are not edited.
- Places that only say "bounded by `max_attempts`" without describing the count are not changed.
- Draft ADR 019 is not edited; its `attempts_left` is left to its own session.

## Status
`completed`

## Result
- The project's claim was confirmed in the code: `_take` (`engine.py`) returns the run to the node
  while its attempt counter is below `max_attempts`, and `_update_stats` (`models/state.py`) raises the
  counter on every return and resets it on departure, so N gives N retries and N + 1 runs in one visit.
  The self-loop count was already pinned by `test_a_self_targeting_transition_is_bounded`.
- The transition hints of `llm` and `ask` now state the count and that the default `3` allows four
  calls or questions.
- `README.md` (the `ask` section) and `docs/architecture/overview.md` (the transitions section) state
  that `max_attempts` counts the retries after the first run, N allowing N + 1 runs and `0` none.
- `examples/approve-and-copy.md` states that its `max_attempts` of `2` is two repeats, three questions
  in all; the template itself is unchanged.
- `test_an_attempts_transition_to_another_node_retries_first` pins the count for an `attempts`
  transition towards another node: `max_attempts` 2 runs the node three times, then takes the route.
- `uv run pytest` (881 passed), `uv run ruff check .` and `uv run ruff format --check .` pass.

## Decisions
- Variant A: the count is stated where the key is defined (`README.md`, the overview) and in the two
  help texts an author reads on their own, not at every mention.
- Renaming the key to `max_retries` was rejected for now: it changes the contract and needs an ADR,
  and the project did not ask for it. Counting the calls instead was rejected: it would silently
  change every definition written against the current count.
- No ADR: existing behaviour is described, no decision changes.

## Open questions
None.

## Next steps
1. Merge the branch into `development` and register this session.
2. Write the answer to `payment-reconciliation` with the merge commit: help and documentation only,
   no contract change, nothing to re-check in its definitions when the pin moves.
3. When Draft ADR 019 is worked on, define its `attempts_left` and `max_attempts` fields in this
   count.

## References
- Branch: `fix/max-attempts-counts-retries`
- ADR 002 (the retry allowance), ADR 017 (`max_visits` beside `max_attempts`), Draft ADR 019
- Changed: `src/workflow_engine/actions/action_llm.py`, `src/workflow_engine/actions/action_ask.py`,
  `README.md`, `docs/architecture/overview.md`, `examples/approve-and-copy.md`,
  `tests/test_engine_transitions.py`
