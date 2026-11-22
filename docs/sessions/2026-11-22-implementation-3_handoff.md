# Session 2026-11-22-implementation-3

## Type
implementation

## Goal
Let a persisted parameter value decode on any Python version, whichever interpreter wrote its codec
name.

## Completion criteria
- Decoding a persisted value resolves its `object_type` by the shared rule of ADR 012: the exact
  registered name first, then an unambiguous bare class name.
- A definition whose `inputs` declare the full path name of another Python version builds.
- A value stored under `pathlib.Path` and one stored under `pathlib._local.Path` both decode to a
  `Path` on the interpreter running the tests, alone and as an item of a collection.
- A name that resolves to no codec still comes back undecoded, as before.
- The architecture note that claimed the fallback already covered a reload is corrected.
- `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- The written spelling of a codec name does not change; the canonical short names of the deferred
  questions note §2 stay an ADR question.
- No change to the ADR 022 report or its branch.

## Status
`completed`

## Result
- `find_codec_by_type_name` reduces a full name that is not registered to its bare class name and
  resolves that by the existing rule, so `pathlib.Path` and `pathlib._local.Path` resolve on 3.13 and
  3.14 alike; an ambiguous bare name still raises.
- `convert_from_dict` decodes through that rule; before, it took the exact name only, so a value
  written on 3.14 stayed an undecoded envelope on 3.13.
- The same rule fixed the second failure the consumer project showed: the persisted `workflow.json`
  declares its inputs under the full name of the interpreter that wrote it, and on 3.13 the
  definition did not build.
- Tests: a path value and a path item of a `deque` decode under both names, an unknown name stays
  undecoded, and an input declared under either full name builds (`tests/test_codecs.py`,
  `tests/test_adr012_inputs_schema.py`).
- Every session of the consumer project `payment-reconciliation`, written on 3.14, was read on 3.13
  with `list-parameters`; its storage was byte for byte unchanged.
- The deferred-questions note §2 now states when the fallback reached decoding.

## Decisions
1. **The reduction lives in the shared rule, not at the readers of persisted names** (ADR 012).
   One rule serves decoding, definitions, `--input`, `set-input` and help. Alternative: reduce only in
   `convert_from_dict` and the definition loader (not chosen — two rules, and authored definitions
   pass the same loader anyway). Cost accepted: a full name whose module part is misspelled
   (`mylib.Path`) resolves to the registered codec of that bare name instead of being refused.

## Open questions
- The written spelling still follows the interpreter, on the state, the definition and the read
  surfaces; the canonical-name question of the deferred-questions note §2 is unchanged.

## Next steps
1. Merge into `development`, then bring `development` into `feature/adr_022-human-readable-run-report`.
2. The Playwright suite of ADR 022, its marker, its dependency group and its CI job.
3. ADR 022 implementation session 3: `README.md`, the overview and the walkthrough; the CI run on the
   branch; merge and freeze.

## References
- Branch: `fix/codec-name-across-python-versions`
- ADR 012, ADR 006
- Changed: `src/workflow_engine/registry/type_registry.py`, `tests/test_codecs.py`,
  `tests/test_adr012_inputs_schema.py`, `docs/architecture/notes/2026-08-18-adr012-deferred-questions.md`
