# Session 2026-10-30-documentation-1

## Type
`documentation`

## Goal
Land the desk letter EX-35 (2026-10-30, `motivation.md`: "a different path every time" says more than
the origin experience) by softening the claim that an agent takes a different path every time.

## Completion criteria
- The sentence in `docs/motivation.md`, section "The starting point", states the probability framing:
  the same path is likely but not guaranteed, and a wrong turn is confident and expensive.
- The same claim in `docs/architecture/purpose.md`, section "Why not one agent with tools and
  prompts", says the same, so the charter does not claim more than the argument.
- The change is committed on `docs/ex-35-motivation-wording`; `What it changed` of EX-35 is filled
  once the branch is merged.

## Scope boundaries
- No other sentence of either document is touched.
- No answer letter: the desk confirms reading through `What it changed`, not through another letter.
- EX-21, the other released letter waiting for this project, is left for its own session.

## Status
`completed`

## Result
Both sentences now say that the model will probably take the same path as last time, that nothing
guarantees it, and that a wrong turn is taken confidently and paid for in full. The economic answer
in `docs/motivation.md` ("nobody can promise the next run takes the same path") already agreed with
this framing and was left as it is.

## Decisions
- `docs/architecture/purpose.md` is changed together with `docs/motivation.md`, although the letter
  names only the latter: left alone, the charter would state a stronger claim than the public
  argument it grounds.

## Open questions
None.

## Next steps
1. Merge `docs/ex-35-motivation-wording` into `development` and add the registry row.
2. Fill `What it changed` of EX-35 with both documents and the commit.
3. Open EX-21 (2026-10-06, one question on what a capture carries, and one change to its
   description) in its own session.

## References
- Branch: `docs/ex-35-motivation-wording`
- Desk letter: EX-35 (2026-10-30, `motivation.md`: "a different path every time" says more than the
  origin experience)
- Changed: `docs/motivation.md`, `docs/architecture/purpose.md`
