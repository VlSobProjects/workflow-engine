# Session 2026-08-25-implementation-4

## Type
implementation

## Goal
Roadmap step 9: make the per-turn `state.json` write crash-safe and protect a session from a second
process, one `fix/` session without an ADR.

## Completion criteria
- `state.json` is written through a temporary file in the same directory and an atomic replace, so an
  interrupted write leaves the previous state intact.
- A mutating engine call on a session another process holds is refused with a named error; the read
  surfaces are never blocked.
- `README.md`, `docs/architecture/overview.md` and item (c) of the recovery note state what the engine
  now guarantees.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No ADR: the lock implements a promise `purpose.md` already states.
- `workflow.json`, `session.json` and `records.jsonl` keep their current write path.
- No new CLI flag and no command for releasing a stale lock.
- The action-registry twin of the provider-registry bug stays out; it gets its own `fix/` branch.

## Status
`completed`

## Result
Both halves of roadmap step 9 are delivered, without an ADR.

The state file is now replaced instead of rewritten: `save_state` writes the new content to a
temporary file in the same directory, flushes it to disk and renames it onto `state.json`. A write
that fails takes its temporary file with it and leaves the previous state readable, so the per-turn
write is safe to be interrupted. `workflow.json`, `session.json` and `records.jsonl` keep their write
path, as the scope stated.

A session is now held by one writer at a time. The hold is a `session.lock` file in the session
directory, created with `O_CREAT | O_EXCL`, carrying the holder's process id and the moment it was
taken. The engine takes it around every call that writes the state — `init_new_session`,
`start_workflow`, `set_inputs`, `set_session_limits` — and releases it when the call leaves by any
path. A second writer is refused with `SessionBusyError`, which reaches the CLI as exit code 4 with a
message naming the holder and the file. The read surfaces take nothing and answer while a run holds
the session.

Documented in `README.md` ("One process per session"), in `docs/architecture/overview.md` (the
storage section and a new "One writer per session" under sessions), and in the recovery note, whose
item (c) is now marked delivered. The roadmap row for step 9 names this session.

Verification: `uv run pytest` 774 passed, `uv run ruff check .` and `uv run ruff format --check .`
clean.

## Decisions
1. **The lock sits on the engine, not on the CLI.** `purpose.md` promises the protection of the
   engine, so a program using the library gets it too. The alternative — guarding the four CLI use
   cases — would have left the library unprotected.
2. **A file created with `O_EXCL`, not an OS advisory lock.** One code path on every platform and
   only the standard library. The cost is that a killed process leaves its file behind, which an OS
   lock would not; the refusal names the file so an operator can remove it.
3. **Held per call, not for the lifetime of the engine.** The state is written only inside those four
   calls. Holding it for the engine's lifetime would have needed a `close()` or a context manager on
   the public API and would have made every use case wrap the engine, for the same protection.
4. **No expiry by age and no `--force` flag.** A node waiting on a slow model call holds its session
   legitimately for minutes, and a hold taken from a live run protects nothing. Releasing a lock left
   by a dead process stays a deliberate act of the operator.
5. **A mistyped session id still reads as a missing session.** The lock is taken before the session
   record is read, so the factory refuses an unknown id first, through `require_session_dir`.

## Open questions
- A lock left by a killed process is released by hand. Whether the engine should ever offer to
  release one — a command, a flag, or a liveness check on the recorded process id — is untouched and
  would be a CLI contract decision.
- The atomic write covers `state.json` only. If a session ever gains a second file rewritten during a
  run, it needs the same treatment; nothing does today.

## Next steps
1. The action-registry twin of the provider-registry bug (`get_registered_actions_info` returns the
   registry dictionary itself) in its own `fix/` branch, as decided at the start of this session.
2. Roadmap step 10: build `load-test-triage` by hand on prepared data.
3. Roadmap step 11: ADR 019 narrowed into Implementing, with the `support-intake` note reformatted as
   a class 2 scenario beside it.

## References
- Branch: `fix/atomic-state-write-and-session-lock`.
- ADRs: none; the lock implements a promise `docs/architecture/purpose.md` already states.
- Changed documents: `README.md`, `docs/architecture/overview.md`, `docs/architecture/roadmap.md`,
  `docs/architecture/notes/2026-08-18-recovery-and-resilience-roadmap.md`.
