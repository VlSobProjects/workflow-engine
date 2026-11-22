# What every storage backend gives a reader

- **Date:** 2026-11-21
- **Trigger:** session `2026-11-20-documentation-1`: the bench reads the session's copy of the
  definition from a file of `JsonStorage`, while database backends (SQLite, PostgreSQL, MySQL) are
  planned before publication, and a backend with a front end that monitors and manages workflows is
  planned after it.
- **Status:** `open`
- **Affected:** ADR 003, ADR 004, ADR 007, ADR 008, ADR 018, ADR 021, ADR 022 (the run report reads the
  definition through the `Storage` contract, the first in-core reader of it, and its viewer is the
  candidate first screen of the web interface below), `docs/architecture/purpose.md` (the boundary on
  user interfaces), the notes
  `2026-11-21-published-contract-and-consumer-requests`, `2026-08-18-adr012-deferred-questions`,
  `2026-08-25-role-separation-answerer-and-operator`

## The idea

`Storage` is an abstract class with one implementation, `JsonStorage`, and what it keeps is visible
only as its files. Database backends will keep the same things elsewhere. The constraint is that a
user of the engine sees no difference: every promise made to a consumer holds on every backend.

The proposal is a read contract: an exactly described set of the facts about a session, and their
formats, that every backend must give, whatever it stores them in. A monitoring and management back
end would be its first reader beside the command line; the command line's read commands would be
another rendering of the same contract.

## What the contract would hold

| Fact | Served today by | Gap |
| --- | --- | --- |
| The sessions there are | `list-sessions` | lists session records under `work_dir`; no status, no filter, no page, not in `README.md` |
| The state of one session | `show-state` | — |
| The parameters and one value | `list-parameters`, `show-parameter` | — |
| The event journal | `show-journal` | — |
| The node records | `show-records` | — |
| The definition the session runs | nothing; `workflow.json` of `JsonStorage` | no surface, and the file is an internal serialization, not the definition as written |
| The artifacts | `show-state` (paths), `export-artifact` | they are files of the session's local work directory on every backend (ADR 003) |
| The session record | `session.json` | no surface |

## Constraints the discussion found

- **Read only.** What an external module receives is a read-only view, never `Storage` itself.
  Writing stays with the engine: a record is written by the engine and by nothing else (ADR 021), and
  a session has one writer (the session lock). A management front end that changes a session does it
  through the engine's commands — `resume`, `set-input`, `set-limit` — not through the store.
- **A reader during a run.** The view answers while a run is in progress, as the read commands do
  today, and states what a reader sees of a turn that is being written.
- **Values.** The records and the journal carry names, never values (ADR 013 §9, ADR 021); the view
  keeps that rule. Values come only from the state, through the codec envelope.
- **Facts, not storage.** The contract names facts and formats, not tables or files, so a backend is
  free in its layout. It is checked by the same tests on every backend, the acceptance criterion the
  note `2026-11-21-published-contract-and-consumer-requests` names for a database backend.

## Alternatives

- **A. The command line is the only read surface.** The monitoring back end shells out to the read
  commands. No new API; a process per read and no query across sessions.
- **B. A read-only Python view over the storage contract**, the command line rendering it. One
  contract, two renderings; a Python API to freeze (level T3 cost).
- **C. A read model the engine writes beside the store** — an index of sessions with their status,
  for queries across sessions. Fast to query; a second copy of facts to keep consistent.

## The web interface the owner plans

Session `2026-11-21-architecture-3` recorded the owner's plan of a web interface to the engine, built
later on the ADR 022 report: the report's viewer renders a fact model the engine builds, embedded in
the document today and served by an API tomorrow. That plan crosses the boundary of `purpose.md`,
which excludes a user interface, and is decided only in an architecture session of its own that
revisits the boundary. A browser cannot read a database backend, so such an interface reads through a
server over the read contract this note proposes, never through the store's files; it is the reader
alternative A cannot serve.

## Open questions

1. Whether the definition gets a read surface now, for the bench, or with the whole contract.
2. Whether the monitoring back end is a consumer of the engine (outside the core, like the bench) or a
   part of it; the answer decides whether B is published at all.
3. What "manage" means for the front end beyond the commands that exist — abort, retry, cancel — and
   whether any of it needs a decision of its own.
4. Whether a session can move between backends, and whether the session record names its backend
   (ADR 004 records the storage settings, so the question exists already).
