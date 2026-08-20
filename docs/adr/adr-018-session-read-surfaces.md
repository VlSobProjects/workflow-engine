# ADR 018: Session read surfaces

## Status
Accepted

## Active branch
—

## Context

An interrupted interview costs nothing today: the session stays paused, a plain `resume` re-presents
the question consuming neither an attempt nor a visit (ADR 013 §6), and nothing expires. What is
missing is not a way back in — it is what the one who comes back can read
(`docs/architecture/notes/2026-08-20-interview-continuation-context.md`).

The reading contract has three problems:

1. **Reading is all-or-nothing.** `show-state` returns the whole persisted state in one document:
   every parameter with its real value, every node output, the artifacts in three spellings, the
   declared inputs, the deliverables. An agent with a bounded context pays for the whole bus to read
   one accumulated list; a human reading a failure scrolls past every parameter to reach the error.
2. **The journal and the guard traces are not in the contract.** `session_events` and
   `guard_results` are persisted in `state.json` and never leave it: no command publishes them. They
   are the half that answers "why did this fail" — which guard answered what on which node, who
   answered when, under which code the node failed, how many visits and attempts there were. Today
   that means opening the state file by hand.
3. **The dump grows with the run and the graph.** `parameters` grows with what the flow accumulates
   and `outputs` with the nodes the graph has, so the one read surface becomes less readable exactly
   on the runs — long interactive collections — where reading matters most.

The neighbouring shape — pushing prior-exchange context into the published question — is rejected
three times over in `docs/architecture/notes/2026-08-20-question-rendering-for-an-audience.md`: the
question block is a disclosure boundary, a plain `resume` must not run code whose effects the engine
cannot check, and a question built from state the block does not carry is not reconstructible from
the run's record. A read command is a different door and none of those reasons reaches it: the
answerer asks the engine for what it needs, through a surface with its own audience and its own
boundary. This ADR is that other door.

Removing `parameters` from `show-state` is a removal, not an addition. The field is documented in
`README.md` and is part of the command result today; every CLI extension so far — `data.export`, the
artifact detail — was additive and needed no ADR. Changing what a caller already gets is why this is
a decision, and it is taken now, while the project is private and the callers are its own tests.

Constraints:
- The journal stores names and codec names, never values (ADR 013 §9). A read surface publishes what
  is persisted; it does not change what is persisted.
- Exit code layout stays as ADR 007 defines it: `0` success, `2` paused, `3` failed, `4`
  command-level setup or resolution error, and info commands report `workflow_status` informationally
  without it affecting their exit code.
- The single rendering rule of ADR 016 (`render_value_as_text`: POSIX form for a path, compact JSON
  for a collection) stays the one way a value becomes text.

## Decision

### 1. `show-state` shows the state of the run, and nothing else

The command keeps the envelope (`workflow_status`, `event_code`, `session_id`, `errors`) and, in
`data`: the timestamp, `flow_id`, `schema_version`, `work_dir`, `current_node`, the visit counters
and budget, the error fields, the artifacts (`artifacts_path`, the relative map, the absolute
detail per ADR 011) and `deliverables`. Artifacts and deliverables stay because they are bounded by
the workflow's declaration, not by the length of the run, and a caller that arrives at someone
else's paused or failed session needs the one surface that says what there is to fetch.

The command additively gains the **guard traces**: `guard_results` as persisted — the latest attempt
per node, so bounded by construction — because they are status, the record of why the run stands
where it stands.

Removed from the result: `parameters`, `outputs`, `inputs`.

### 2. Parameters are read through two commands, each with one shape of result

- `list-parameters --session-id <id>` returns the list of parameters as `{name, type, source_node}`
  — the codec name and the node that wrote the value, never the value itself.
- `show-parameter --session-id <id> --name <name>` returns one value. The plain output is the
  ADR 016 rendering. With `--json`, `data` carries the codec envelope exactly as the state persists
  it — the codec name and the encoded value — so a machine reader keeps the type and can feed the
  value into `set-input` of another session without re-encoding. `data` names the parameter and its
  writing node beside the envelope: the same two fields `list-parameters` publishes, so reading one
  value does not require the listing as well.

Two commands rather than one with a selector, because each then has a single shape of result — a
list, or one value — rather than a `data` block that changes shape with a flag.

A name that does not exist is a command-level resolution error: `command_status: error`, exit
code `4` — the same answer `help-component` gives for an unregistered component. An empty success
would hide a typo from a script.

### 3. The journal gets its own command

`show-journal --session-id <id> [--tail <n>] [--node <node_id>]` publishes `session_events` as
persisted: timestamp, code, actor, event id, details — names, codec names and ordinals, never
values, which is what the journal holds (ADR 013 §9). Without flags the whole journal is returned:
asking for the journal is an explicit act, and the reader who performs it has chosen the size.
`--tail` bounds the answer to the last `n` events; `--node` filters to the events that name the
node. The two compose: the filter runs first, so the pair reads as "the last `n` events of this
node". The answer reports how many events it carries next to how many the whole journal holds,
because a bounded read that does not say it is bounded reads as the full record. A `--tail` below
`1` is a command error rather than an empty answer, for the reason an unknown parameter name is.

### 4. The new commands are info commands

`list-parameters`, `show-parameter` and `show-journal` join `show-state` in the info command set of
ADR 007: they report `workflow_status` informationally and exit `0` on command success regardless of
where the workflow stands, `4` on resolution errors.

## Alternatives considered

- **Keep `parameters` in `show-state` and add the narrow commands additively.** No removal, no
  breaking change. Rejected: the unbounded dump remains the default read, the same data acquires two
  contract homes to keep aligned, and the removal only gets more expensive once the project is
  public. The note already records the choice to do it now.
- **One command with selector flags** (`show-state --section parameters`, `--param <name>`).
  One entry point, but the shape of `data` then depends on the flags, and every consumer branches on
  the combination. Rejected for the same reason the help surface has `help-components` and
  `help-component`: one result shape per command.
- **Move the journal into `show-state`.** Publishes the missing half, but moves the problem rather
  than solving it: a long run has many events and the status document becomes the dump the parameter
  removal just cured. Rejected.
- **A forced default tail on `show-journal`.** A bound by default protects a careless reader, but
  invoking a journal command is already the explicit choice to read the journal; a default tail
  makes the full read a two-step dance for everyone to protect a reader this project does not have.
  The bound is available, not imposed.
- **A separate ADR for the journal command.** The command is additive and could stand alone.
  Rejected: "`show-state` shows the state of the run, and nothing else" holds only if the journal
  has its own door; splitting the decision would let 018 promise a door another decision might not
  build. The decision here is the boundary of the read contract; the commands are its mechanics.
- **Pushing context into the published question** — rejected before this ADR and not reopened; see
  Context.

## Consequences

- **The `show-state` result shrinks incompatibly.** `parameters`, `outputs` and `inputs` leave the
  document; every consumer of the old shape — today, this project's own tests and `README.md` —
  changes with the implementation. Taken deliberately while the project is private.
- **The declared-inputs interface loses its only read surface.** "What must I bind before the run"
  was answered by `show-state`'s `inputs` field; until a workflow-definition introspection surface
  exists, the workflow definition itself is the reference. This sharpens the missing-introspection
  point of `docs/architecture/notes/2026-08-18-adr012-deferred-questions.md`; it does not decide it.
- **`outputs` loses its surface without a replacement.** The rendered text of a node's last output
  becomes unreadable from the CLI. A dedicated surface waits for a scenario that asks for one; the
  current output of a paused interactive node is not affected, because a plain `resume` re-presents
  the question (ADR 013 §6).
- **The guard traces and the journal become contract.** Their persisted shapes, so far internal to
  `state.json`, freeze on first publication: field names, event codes, `details` keys become things
  a consumer may rely on.
- **The transcript question stays open.** Reading parameters gives back what the flow accumulated —
  the `qa_log` pattern that already works — not the questions that were asked. The engine still
  keeps no record of the exchange itself, and a surface cannot publish what is not persisted;
  changing that would contradict the journal's stance on values and is deferred until a flow forces
  it.
- Three commands and two removals to document: `README.md`, `docs/architecture/overview.md` and the
  CLI contract version move with the implementation.

## Related ADRs

- ADR 006 — owns the journal this ADR publishes.
- ADR 007 — the CLI contract and exit code layout this ADR extends and, for `show-state`, narrows.
- ADR 009 — the one-shape-per-command precedent (`help-components`/`help-component`) and the
  unknown-name answer this ADR reuses.
- ADR 011 — the artifact fields `show-state` keeps.
- ADR 012 — declared the `inputs` field this ADR removes from `show-state`.
- ADR 013 — the exchange whose continuation this ADR serves; its §9 bounds what the journal surface
  can ever show.
- ADR 016 — the rendering rule `show-parameter` uses for its plain output.

## Implementation notes

- Feasibility verified against the state model: each parameter is persisted with its codec and its
  writing node (`ActionParameter`: `source_node_id`, `codec`; the envelope is
  `codec.convert_to_dict(value)`), so `list-parameters` and the `--json` envelope read what is
  already there.
- `guard_results` keeps the latest attempt per node by construction; surfacing it adds no growth to
  `show-state`.
- The three artifact spellings in `show-state` (`artifacts_path`, relative map, absolute detail) are
  kept as-is by this decision; consolidating them is a candidate the implementation discussion may
  raise, since the result is breaking anyway. The implementation kept them.
- `CONTRACT_VERSION` does not move. The draft expected it to, but the only such constant versions the
  operator help payloads (ADR 009) and is stamped into nothing this decision touches; raising it would
  announce a change to help consumers that did not happen. Whether the command results as a whole
  should carry a version of their own is a question this ADR leaves where it found it.
- The `type` of a parameter is the registered codec name, the key the state persists in `object_type`
  and the one `help-component --component-type codecs` lists. It is a fully qualified Python name, so
  it can change with the interpreter (`pathlib.Path` reads as `pathlib._local.Path` on 3.13); a caller
  that pins the literal pins a Python version, and the bare form (`Path`) is what `set-input` takes.
- The plain output of each command is rendered by the command, as the help surfaces do, rather than
  left to the generic `Data: {...}` line: a journal printed as one Python dict is not a surface a
  human reads. `--json` remains the shape a machine reads.

## Change log

- 2026-08-21 — Implemented on `feature/adr_018-session-read-surfaces`. Amendments made while
  building it: `CONTRACT_VERSION` stays where it is, because it versions the help payloads and not the
  command results; `show-parameter --json` carries the name and the writing node beside the envelope;
  `show-journal` reports the size of its answer next to the size of the journal and refuses a `--tail`
  below `1`; each command renders its own plain output. `README.md` and
  `docs/architecture/overview.md` describe the delivered surfaces.
- 2026-08-20 — Drafted from `docs/architecture/notes/2026-08-20-interview-continuation-context.md`
  and the decisions of session `2026-08-20-architecture-7`: the run-state boundary of `show-state`
  (artifacts and deliverables stay; parameters, outputs and inputs leave; guard traces join), the
  two parameter commands with the codec envelope under `--json`, the unbounded-by-default journal
  command with `--tail` and `--node`, and one ADR for the whole boundary.
