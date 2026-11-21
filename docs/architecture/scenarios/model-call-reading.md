# A model call read as a measurement

- **Identifier:** `model-call-reading`
- **Class:** `2`
- **Answerers:** a model, through the one `llm` node of the definition under test — the `fake` adapter
  in this scenario, a model server of the bench's server role in a real reading; an external program,
  the bench, that drives every command through the command line and judges nothing inside the run; no
  human answers a step.
- **Input data:** the neutral public example task of `llm-test-bench`: a frozen set of items, each one
  input value for the node, the one-node definition the bench builds from its template, and the
  scripted replies of the `fake` adapter per item. All of it lives in the bench's repository, which
  does not carry the task yet: it is a step of the bench's first phase.
- **Expected paths:** the answered call, whose reply the answer declaration accepts; the refused reply,
  which the declaration does not accept (`llm_answer_invalid`); the failed call, a scripted provider
  failure retried up to `max_attempts`; the setup refusal, a missing input or an unconfigured provider;
  and the recount, which starts no session. Each is selected by the script of the item. Details in the
  body.
- **Ends with:** per session, end of workflow with exit code `0` on the answered path; failure with
  exit code `3` under the node's code when the template routes a refused reply or an exhausted
  provider failure to failure; exit code `4` with nothing run on a setup refusal. The reading ends when
  the bench has kept the four things below for every item and repeat; the recount ends in the bench,
  with no engine command.
- **ADRs exercised:** ADR 005, ADR 007, ADR 011, ADR 012, ADR 014, ADR 017, ADR 018, ADR 021

## The consumer

`llm-test-bench` measures how language models perform on a task its user brings: which model, settings
and prompt are safe enough, which of the safe ones costs least, what moves when one thing changes, and
whether the same configuration gives the same result twice. It is a project of the owner outside this
repository; the desk letter EX-37 (2026-11-18, llm-test-bench joins the desk) introduced it and asked
for this document, and EX-40 (2026-11-20, the engine keeps a scenario of the bench's use) promised it.

The bench calls a model only through the engine, uses only the command line and never the Python API,
and raises a need the engine does not meet with the engine instead of working around it. That makes
it the strictest reader of the engine's published surfaces so far: it parses every result, keeps it,
and compares two runs by what they left behind. The point of this scenario is that a change of the
engine which breaks the bench is visible here, on the engine's side, before the bench finds it.

The scenario is one concrete task, not the bench as a whole: one reading of the bench's example task,
then one recount of it.

## The reading

The object under test is a definition of one `llm` node, built by the bench from its template:

- a declared input carries the item (ADR 012);
- the node names a provider, never an endpoint, carries the prompt as template text over that input,
  declares the answer and its `format`, sets `record: true` — which the bench requires of every `llm`
  node — and bounds its retries with `max_attempts`;
- its transitions end the workflow on an accepted answer, retry the node on the transient classes, and
  fail or end on the rest, as the template decides.

The bench writes one configuration file per run: the provider block of its server role, named as the
node names it; `external_modules` for its own components and those of the task package (ADR 005); and
a runtime root of its own. Under that configuration it runs one session per item and per repeat:

1. `run --workflow-file <definition> --input <name>:<type>=<value> --config <file> --json`, which
   creates the session, binds the item and runs it in one call.
2. `show-records --session-id <id> --json`, the record of the one visit — or of each attempt where the
   node retried — with the account of the call in its `details`.
3. `export-artifact --session-id <id> --target-dir <dir> --all --json`, which copies the prompt and
   the reply of every attempt out of the session.
4. The command result of step 1 itself, kept as it was printed.

It keeps the four results and the definition it passed, frozen by hash. In this scenario the provider
is the `fake` adapter: the replies are scripted per item in the provider block's `replies` or as the
`reply` or `error` option of the call, so the route of every item and every kept file is known before
the run. A reading against a model server is the same commands under another provider block; the
difference between the two is what the bench measures.

## The recount

The bench evaluates the kept replies again with its own code and starts no engine session. Nothing of
the engine runs, so the recount exercises one thing only: that what the reading kept is enough. The
reply artifact is the raw text the model returned, before the answer declaration read it, so a changed
evaluation needs no model call; the record names which reply belongs to which attempt by the visit and
attempt ordinals it shares with the artifact names.

## The surfaces the bench takes

The list is what a change of the engine must not break without a decision. A surface marked
*implementation* is one the bench must not rely on: it is how the engine stores something today, and
the engine does not promise it.

| Surface | What the bench reads or writes | Where it is described | ADR | Kind |
| --- | --- | --- | --- | --- |
| The command result under `--json` | one JSON document on stdout per command, `command_status` `error` included, never usage text | `README.md` (Reading a session); overview (CLI) | ADR 007 | contract |
| Exit codes | `0` success, `2` paused, `3` failed workflow, `4` setup or resolution error | `README.md`; overview | ADR 007 | contract |
| `run`, `--workflow-file`, `--config`, `--work-dir` | a session created, bound and run in one call, under a configuration and a runtime root of the bench's | `README.md` (Configuration file) | ADR 007, ADR 008 | contract |
| `--input NAME:TYPE=VALUE` and the `inputs` block | the item bound under a registered codec; an unbound required input refused with `4` | `README.md`; overview (inputs) | ADR 012 | contract |
| `external_modules` | the bench's and the task package's components registered at bootstrap | `README.md` (Writing a custom function) | ADR 005 | contract |
| The provider block | `adapter`, `base_url`, `model`, `api_key_env`, `options`, and nothing beside them | `README.md` (Configuring a provider) | ADR 014 | contract |
| The `llm` node | `provider`, `prompt`, `answer`, `format`, `options`, `record`, `save_call_as`; `max_attempts` counting the retries after the first run | `README.md` (Calling a model) | ADR 014 | contract |
| The error classes of a call | the six adapter classes and the three of the action, each a routable node error | `README.md` (When the call fails) | ADR 014 | contract |
| `max_visits` | a cap on the node's entries, refused under `max_visits_exceeded` | `README.md` | ADR 017 | contract |
| `show-records --json` | one record per concluded visit: ordinals, status and code, guards, transition, writes, artifacts, and the `llm` `details` — `provider`, `model`, `model_requested`, `model_answered`, `status`, the error class, `usage` | `README.md` (What a call leaves behind); overview (Node records) | ADR 021, ADR 014 | contract |
| The prompt and reply artifacts | `<node_id>.prompt.<visit>.<attempt>` and `<node_id>.reply.<visit>.<attempt>`, the reply absent on a failed call | `README.md` (What a call leaves behind) | ADR 014, ADR 021 | contract |
| `export-artifact --all` | every artifact of a completed, paused or failed session copied out | `README.md` (Retrieving the result) | ADR 011 | contract |
| `show-parameter --json` | a value in the codec envelope that `--input` and `set-input` of another session accept unchanged — the way one step is tested alone on what an earlier run kept | `README.md` (Reading a session) | ADR 018, ADR 012 | contract |
| The `fake` adapter | scripted `replies` in the provider block, `reply` and `error` as call options, no network | `README.md`; `help-component --component-type providers --component-name fake` | ADR 014 | contract |
| The session's copy of the definition | the file `workflow.json` in the session's storage directory | overview (Storage) | — | **implementation** |

The session's copy of the definition is not a surface. `JsonStorage` keeps it because it is the only
storage backend today; a database backend keeps it elsewhere, and no command prints it. The file is
also not a copy of what the bench passed: it is the engine's serialization of the definition after
parsing, so its hash differs from the hash of the bench's file and may change with an internal
refactoring while the definition stays the same. The bench's evidence of what ran is the definition
file it passed to `--workflow-file`, frozen by its own hash.

## Expected paths

1. **Answered.** The script answers the item with a reply the declaration accepts; the values are
   bound, the workflow ends, exit code `0`. One record, `status` `answered`, `model_answered` the model
   the adapter reported; one prompt and one reply artifact. The reference path.
2. **Refused reply.** The script answers with a reply the declaration refuses; the node error is
   `llm_answer_invalid`, the raw reply is still the reply artifact and the output text, and the call
   in the record is an answered call with no error class. Where the template ends or fails is the
   template's decision; the kept reply is what the recount evaluates either way.
3. **Failed call.** The script fails the call under a transient class; the node retries until
   `max_attempts` is exhausted and fails under `max_attempts_exceeded`, exit code `3`. One record per
   attempt, each with its error class; a prompt artifact per attempt and no reply.
4. **Retried and answered.** The script fails the first attempt and answers the second; two records
   with the same visit and attempts `1` and `2`, the reply artifact only on the second.
5. **Setup refusal.** The item is not bound, or the node names a provider the configuration lacks;
   exit code `4`, nothing run, and under `--json` one command result with `command_status` `error`.
6. **Recount.** The kept replies of paths 1 to 4 evaluated again by the bench; no engine command.

## Open decisions the scenario still lacks

1. **A read surface for the definition.** No command prints the definition a session runs, as ADR 018
   already records. Until one exists the bench's own file is the evidence. Whether the engine
   publishes one belongs to the note `2026-11-21-storage-read-contract`.
2. **Whether the surfaces above are checked.** This document describes them; nothing tests them as a
   set. A contract the engine publishes and tests, and a consumer asking for a change to it by a
   request letter, is the note `2026-11-21-published-contract-and-consumer-requests`.
3. **What a provider reports about a call.** The options the adapter sent and the metrics a provider
   reports are deferred to an ADR on an open member of the reply (EX-38, 2026-11-19, the environment
   a model call ran in). Where the bench relies on their names, they are added to the table above.
4. **The values of every visit.** A visit tested alone needs what it read at its entry, and the state
   keeps only the last write of a parameter; deferred to an ADR (EX-39, 2026-11-19, the value written
   at every visit of a node). Until then a node visited more than once cannot be tested alone.
5. **The pin.** The bench pins a commit of `development`; a tag is what the engine undertakes to keep
   (EX-40). A pin on a range of versions needs the published contract and a version policy first.
6. **The list of ADRs.** `ADRs exercised` is the bench's own reading in EX-37. Any `llm` definition
   also stands on ADR 002 (transitions, `max_attempts`) and ADR 016 (the prompt as template text);
   they are added when the bench confirms it relies on them.
