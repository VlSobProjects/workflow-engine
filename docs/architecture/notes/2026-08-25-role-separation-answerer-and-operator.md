# Two roles at the engine's boundary: the answerer and the operator

- **Date:** 2026-08-25
- **Trigger:** the discussion that followed session `2026-08-25-implementation-5`, on how the phase
  gate can be run honestly. If the exit scenario is to be authored by a party that does not know the
  engine, that party must not read the engine's internals — and the run must be able to prove it
  did not.
- **Status:** open
- **Affected:** ADR 007 (the CLI contract publishes one undifferentiated command set), ADR 018 (the
  read surfaces are exactly what a blind answerer must not have), ADR 019 (a renderer over the
  question document is the natural narrow entry for the answerer), ADR 003 and ADR 004 (the storage
  boundary and the session record, if the internals move out of files), ADR 008 (the working
  directory), `2026-08-19-interactive-exchange-publishing-boundary.md` (`actor` carries no
  identity), `2026-08-21-agent-instruction-and-skill.md` (the instruction the answering agent is
  given), scenario `workflow-authoring` (both variants of its answerer)

## What is being proposed

Two roles at the boundary of the engine, named and separated:

- the **answerer** walks the nodes — receives the published question, sends the answer, learns that
  the run waits — and nothing else;
- the **operator** owns the session — state, parameters, journal, records, export, limits,
  configuration.

Today there is one role. Every command of ADR 007 and every read surface of ADR 018 is available to
whoever holds the command line, so an answering agent that is curious can read the state it is
supposed to be blind to, and no one can tell afterwards whether it did.

The motivations are two and they should stay apart:

1. **Product.** An answerer does not need the operator's surfaces, and handing them over is a
   contract wider than the role. This is worth a decision on its own merit.
2. **Experiment hygiene.** The phase gate wants a blind author. Blindness has to be provable, not
   promised.

## What a decision can settle, and what it cannot

**A capability model is ADR territory.** Which calls belong to the answerer, which to the operator,
and what a role's refusal looks like. That is a contract question over ADR 007 and ADR 018 and it is
useful regardless of the experiment.

**Enforcement is not.** A check inside a process started by the same OS user that owns the session
holds only the honest. Concretely, the password-in-configuration idea does not survive contact:

- the configuration file is chosen by a command flag with a default under the current directory, so
  an answerer can pass another one, or none;
- the answerer must be able to read the configuration to run the engine at all, so the secret is in
  its hands by construction;
- and the read commands are conveniences over files. `state.json`, `records.jsonl`, `workflow.json`
  and `session.json` are on disk; a locked CLI locks the front door of a house with open windows.

**The enforceable boundary is the file system and the process, not the command set.** Three shapes
that actually hold:

- a separate OS user without read access to the session directory — the only true barrier, no engine
  change, the cost is machine setup;
- a narrow entry instead of the full command line: the answerer is handed something that publishes
  the question and takes the answer, which is the direction ADR 019's renderers already point in;
- a container or a separate machine with only the data directory mounted.

For an experiment, the narrow entry plus an audit is enough: the answerer's transcript is kept whole,
and a run in which an operator command appears is void. Blindness proved by record rather than by
lock.

## What the discussion added for a later phase

- **A database storage.** Moving what belongs to the engine's internals out of readable files and
  into a storage of its own — a large task, wanted for its own reasons, and it changes this question:
  the state stops being a file anyone in the directory can open, and gains credentials that then have
  to be kept from the answerer.
- **The working directory stays shared.** Sessions and artifacts are the run's own data; separating
  them from the answerer's reach is neither obviously possible nor obviously right — the deliverable
  is often exactly what the answerer works with.
- **The configuration lives apart** from the working directory and is handed to a session as an
  environment parameter rather than found next to the data.

## Open questions

- What is in the answerer's capability set exactly — does it include "which question is pending",
  "what did I answer last", "is the run still alive"?
- Is the narrow entry a mode of the existing command, a second entry point, or a renderer? ADR 019
  decides the document; who serves it is not decided.
- Does a role need an identity? `actor` is recorded without one today, so a record cannot say which
  answerer answered.
- Does the database storage make the boundary easier or only move it to a credential?
