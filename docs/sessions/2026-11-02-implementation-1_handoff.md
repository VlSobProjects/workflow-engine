# Session 2026-11-02-implementation-1

## Type
`implementation`

## Goal
Answer two of the three engine gaps the `payment-reconciliation` project raised: class a 5xx refusal
of an oversized prompt as `context_overflow`, and make a failed state save name its cause and wait out
a passing refusal of the rename.

## Completion criteria
- The shared status rule of the provider package classes a 5xx whose body carries an overflow marker
  as `context_overflow`, proven through `ollama_systemone` with the server's own refusal wording.
- `JsonStorage.save_state` reports the class and the message of the original exception beside the path.
- The rename onto `state.json` is attempted again after a `PermissionError`, proven by a patched rename
  and, on Windows, by a real reader holding the file open.
- The documentation the change made inaccurate is corrected in the branch.
- `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- The third gap, setting the context of a decision model, is not touched: it needs a check against a
  live server first.
- Keeping the body of a refused call in the record of the run is not touched: ADR 014 §4 lists the
  fields of the call account and ADR 021 §3 keeps payloads out of records, both accepted.
- `append_record` and `save_workflow` lose the cause of their failure the same way and are left as
  they are, by the owner's decision.

## Status
`completed`

## Result
- `classify_status` reads the overflow markers for a status in the 4xx and the 5xx range alike; a 5xx
  without a marker stays `transient`. The operator descriptions of `openai_compatible` and
  `ollama_systemone` say so. The refusal `Context size has been exceeded.` under a 500 is a test case
  of the `ollama_systemone` suite, and a 5xx overflow one of the `openai_compatible` suite.
- `save_state` raises `StateLoadError` with `<path>: <exception class>: <message>`.
- `write_json_atomically` replaces the target through `_replace_retrying`: after a `PermissionError`
  it waits 0.05, 0.1, 0.2, 0.4 and 0.8 seconds between attempts, then raises the last refusal as it
  is. Covered by a patched rename that refuses twice, one that always refuses, and a Windows-only test
  with the state file held open by a reader that lets go after 0.2 seconds.
- A by-hand probe confirmed that on Windows a rename onto a file held open by a reader is refused with
  `PermissionError` (WinError 5) when no retry is allowed, so the Windows test exercises the retry.
- `docs/architecture/overview.md` describes the retry and the reported cause.
- Run: `uv run pytest` (862 passed), `uv run ruff check .`, `uv run ruff format --check .`.
- Not run: a call against a live model server; a run of the project's definition at its site.

## Decisions
- The markers are read in the shared rule rather than in `ollama_systemone` alone, so one server never
  reports two classes for the same status and body. No ADR: ADR 014 §5 fixes the classes, not the
  mapping of a status onto them.
- The rename is retried on every platform, only after a `PermissionError`; elsewhere such a refusal
  is permanent and costs a failing save about a second and a half.
- No ADR for the storage change: the atomic write itself came in under a `fix/` branch.

## Open questions
- Whether the body of a refused call belongs in the record of the run, as a `details` field or as an
  artifact beside the prompt; either changes what accepted ADR 014 §4 and ADR 021 §3 decide.
- Whether the decision endpoint accepts a load-only request with a context option, and whether the
  server then reports that context for the loaded model.

## Next steps
1. Answer the project: the overflow note fixed by this branch, the body of a refused call deferred
   with the reason above; the state save note fixed by this branch.
2. An investigation session against a live server for the context of a decision model, then an
   implementation of the load in the provider block under ADR 014 §2, with the context the server
   reports checked after the load; or, if the load is refused, the answer that the context is the
   operator's model variant and the project's bound on the questions of one call.
3. An architecture note on keeping the body of a refused call in the record of the run.

## References
- Branch: `fix/overflow-on-server-error-and-save-cause`
- ADR 014 (§2, §4, §5), ADR 021 (§3)
- Changed: `src/workflow_engine_providers/openai_compatible.py`,
  `src/workflow_engine_providers/ollama_systemone.py`, `src/workflow_engine/storage/json_storage.py`,
  `docs/architecture/overview.md`, the tests of the adapter package, the `ollama_systemone` adapter
  and the JSON storage
