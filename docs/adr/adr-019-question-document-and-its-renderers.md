# ADR 019: The question document and its renderers

## Status
Draft

## Active branch
—

## Context

ADR 013 gave the engine one interactive action and one answer contract, and decided in §6 that "the
engine has no way to know who is reading, so it declares nothing about the intended audience". The
published `question` block of §3 followed from that: with no reader named, nothing could be left out,
so the block carries the node id, every presentation field and the answer declaration, inside a
command result that carries the state of the run beside it.

Driving the ADR-0083 coverage scenario by hand from the answerer's seat (session
`2026-08-21-investigation-2`) showed what that produces:

- The block states what to answer and never how. The answer envelope of ADR 013 §4 is documented in
  `README.md` and absent from the block, while `generic_error_code` — half of the same contract — is
  published. An answerer holding only the paused result cannot compose a valid answer.
- `node_id` is published to a reader that cannot use it: `resume` addresses a session, not a node.
- One paused result carries the instruction three times, the status three times, the session
  constants on every turn and its empty fields always. For a model that answers, every repeated
  field is context it pays for on every turn of an interactive flow.
- Every bound the author sets — `max_attempts`, `max_visits`, the `minimum` of a collecting loop —
  is invisible to the party it binds.

The discussion of session `2026-08-22-architecture-1` reached a diagnosis rather than a list of
fixes. ADR 013 §1 — one answer contract, whoever answers — is right: the engine does not care whose
hand sent the JSON. ADR 013 §6 and alternative G drew the wrong conclusion from it: "the engine does
not know the reader" justifies publishing the least that serves every reader, not publishing
everything. That was a decision, frozen with ADR 013, and a note cannot change it. This ADR
supersedes it.

Two facts of the engine bound the decision. The only template mechanism is reference interpolation
(ADR 016): `${param.}`, `${output.}`, `${artifact.}` inside the presentation fields of `ask`; there is
no layout templating and no LLM node in the tree (ADR 014 is Draft). And no guard reads the
counters: the only exit from a re-ask loop is the engine's `max_attempts_exceeded` failure.

## Decision

### 1. What an interactive action publishes

`BaseInteractiveAction` publishes an instruction — what the answerer has to do — and the protocol:
the form in which the result has to be sent so that the engine accepts it and the run continues.
Nothing else. The answerer does not know the graph: the document names no node, no transition and no
session internals. Whether the run proceeds, and where, is decided by the node's guards on the answer;
the answerer pushes the process, it does not steer it.

This restates ADR 013 §1 with the reader named: the document is addressed to the party that answers.
An operator watching the run reads the session commands of ADR 007 and ADR 018, not the document.

### 2. The question document

The engine builds one typed document from the paused node. Its fields are the presentation the author
wrote (`title`, `goal`, `context`, `instruction`, the list fields, the error catalogue), the answer
declaration, the protocol (§5) and the runtime values of §6 the author referenced. A field the author
did not set is absent from the document, not empty. The document is the published contract that
ADR 013 §3 called the `question` block, typed and versioned; `PresentResponse` stays internal.

The same document is what the future LLM node hands its model (ADR 014): the prompt of that node is
this document rendered, not a second assembly.

### 3. Renderers

A renderer turns the document into text for one audience. Core renderers are code, registered like
every other component (ADR 005), and ship in three forms: `text` for a human reading a terminal
(indented sections, tables where a field is tabular), `md` for a model (Markdown headings, lists and
tables), and `json` (the document serialized, present fields only). External renderers register under
their own name from an external module.

A renderer is pure: it reads the document and returns a string. It runs on every re-present and must
be harmless to re-run.

### 4. Selecting the renderer

The renderer is chosen, in this order of precedence: the `--format <name>` option of the publishing
command; the `format` key of the node; the `format` key of the workflow; the core default. An author
cannot forbid the caller's choice: the same flow is answered by an agent today and by a human who
takes over tomorrow (ADR 013 §6), and the taking over is the call. An unknown name is a command error
(exit code `4`) at call time and a configuration error at build time.

### 5. The protocol is published, and it is one

The answer protocol of ADR 013 §4 stays single and is not configurable: a parser decides what reaches
the state, so an alternative answer form is a failure surface in a way an alternative question form
is not. The document publishes it, rendered for the audience: as a worked example for a model, as a
plain statement of which field carries what for a human, as a schema for `json`.

Every codec declares the form of a value it accepts — a schema fragment and an example — as part of
its registration metadata (ADR 005, ADR 009). The protocol section is generated from the answer
declaration and those forms; the codec name alone, which is what the block publishes today, tells an
answerer nothing it can act on unless it already knows the engine's Python types.

### 6. The bounds become references

ADR 016 gains a fourth reference prefix, `node.`, with a closed vocabulary resolved at presentation
time: `attempt`, `max_attempts`, `attempts_left`, `visit`, `max_visits`, `collected`, `minimum`,
`nodes_visited`, `max_nodes_visited`, `last_error`. An author who wants the answerer to know how many
attempts remain writes `${node.attempts_left}` into the instruction; the engine does the arithmetic. An
unknown name is a build-time configuration error, like a malformed template. Conditions on these
values are written in prose by the author and read by the answerer; the engine supplies values, not a
template language.

### 7. `instruction-only` mode

An author who has a finished prompt for a node sets the node's `instruction_file` to a path relative
to the workflow file. The file is template text in the sense of ADR 016: every reference, `node.`
included, is interpolated. In this mode the document carries the interpolated file as its
instruction and the protocol of §5, and nothing of the presentation fields: the author who chose the
mode has written the options and the explanations, and the engine does not repeat them. The error
catalogue is protocol — the answerer has to name the codes — and is published in both modes.

### 8. One command publishes the document

A new command publishes the document of the paused node, rendered by the selected renderer, and
nothing else. `run`, `resume` and `show-state` keep the command result of ADR 007 and its `--json`
presenter: they report the run to the party that operates it. The `question` block leaves `data`; a
paused result says that the run is paused and where the document is obtained.

### 9. Audit copy

On request of the workflow (a key, off by default) the engine writes every rendered document into the
session directory, named by node, visit and attempt, so that what an answerer was shown is kept beside
the journal. The journal keeps recording the event, not the text.

## Alternatives considered

### A. Leave ADR 013 §6 and tidy the block
Add the envelope to the block, drop `node_id`, stop `description` defaulting into the result message.
Cheapest, and every finding above returns in a year, because the block still has no addressee and no
rule says what may be left out. Rejected: the defect is in the decision, not in the field list.

### B. The engine publishes raw, an external layer adapts
Keep the command result as is and let a Skill or a driver script format it for a model. Costs nothing
in the core. Rejected: every scenario this engine is written for names a model as the answerer, and an
adapter nobody has written is a promise, not an architecture. The rendering note recorded this as the
state of things, not as a choice.

### C. An `audience` declared on the node (ADR 013 alternative E)
The author says who answers, the engine renders for them. Rejected again for the reason ADR 013 gave:
the same node is answered by whoever calls next, and an escalation to a human would receive a
document shaped for a model. §4 keeps the author's choice as a default under the caller's.

### D. Text templates for the core renderers
Ship the core renderers as `string.Template` files. Rejected: `string.Template` has no conditionals
and no loops, so it can neither omit the heading of an absent field nor lay out a list of options.
Core renderers are code; a text template is one possible external renderer, fed already rendered
sections.

### E. A `state.` reference prefix
Let template text reference any field of the state model, validated at build time against its
schema. Rejected: it makes the field names of `StateModel` a contract an author writes against, so
every rename costs a migration of foreign workflow files; and the per-node values an author actually
needs (`attempts_left`, `max_attempts`) are not fields of the state at all. The closed `node.`
vocabulary covers the need without freezing the state model.

### F. A configurable answer format, symmetric to the renderer
Register answer parsers the way renderers are registered. Rejected: a parser decides what reaches the
state, so an external parser is a second decoding rule at the engine boundary, the thing ADR 013 §4
removed. One protocol, published well, is the cheaper guarantee.

### G. Keep the document inside the command result, clearly separated
Two keys in one JSON: telemetry and document. Rejected: the wall stays inside one payload that every
reader still receives whole, which is the mixture this decision removes.

### H. A guard over the counters, in this ADR
The `node.` values are also what an author needs to route "after N attempts, escalate" instead of
failing. Not decided here: routing is a decision of its own with its own proof, and this ADR names it
as a dependency rather than widening.

## Consequences

- Enables: an answerer — human or model — that can answer from the document alone; a document a model
  pays for once per field; bounds the answerer can see; a prompt the author owns, interpolated by
  the engine; one document that the LLM node of ADR 014 consumes.
- Costs: a typed document class with a schema version; three core renderers and a registry for
  them; a `format` key on node and workflow and a `--format` option; a new command and the removal of
  the `question` block from the `run`/`resume` result (a breaking change of the ADR 007 contract,
  before any external caller exists); a value form on every core codec and a rule for external codecs
  without one; a fourth prefix in ADR 016 with its build-time validation; an `instruction_file` key
  with relative-path resolution against the workflow file; an optional audit copy; the README, the
  example walkthroughs and the overview rewritten for all of it.
- Closes off: publishing `PresentResponse` or the state to the answerer; per-node answer formats; an
  open `state.` reference.
- Supersedes: ADR 013 §3 (the `question` block inside `data`) and §6's last sentence (no declared
  audience); alternative G of ADR 013 is answered by §2 (the document is typed, not the internal
  class).
- Amends, when accepted: ADR 007 (a publishing command; the `question` block leaves the run result),
  ADR 016 (the `node.` prefix; `instruction_file` as template text), ADR 005 and ADR 009 (renderers
  as components; the value form in codec metadata).
- Constrains: ADR 014 — the LLM node's prompt is the rendered document.
- Depends on, to be opened: the counter guard (alternative H).
- Leaves open: whether an external codec without a value form is refused or published as a string;
  whether the audit copy is a file or an event; whether a later transport (ADR 013 alternative D)
  carries the document or a reference to it.

## Related ADRs

- Supersedes in part: ADR 013 (§3, §6, alternative G).
- Depends on: ADR 005 (registration), ADR 007 (command contract), ADR 013 (the answer contract it
  publishes), ADR 016 (interpolation), ADR 017 (the counters `node.` reads).
- Touches: ADR 009 (codec metadata), ADR 018 (the session read surfaces keep the telemetry).
- Constrains: ADR 014.
- Promoted from: `docs/architecture/notes/2026-08-20-question-rendering-for-an-audience.md`,
  `2026-08-21-answer-document-and-its-audience.md`,
  `2026-08-21-command-result-cost-for-a-machine-reader.md`.

## Implementation notes

No POC is foreseen: the pause, the interpolation, the registries and the codec metadata exist, and
no open question needs code to answer it. Reuse rather than rebuild: `answers.question_block` is the
seed of the document class; `text_interpolation.py` gains the prefix; `CodecMetadata` gains the value
form; `renderers/simple_render.py`, which formats the internal class, is replaced by the `text`
renderer over the document.

## Change log

- 2026-08-22: opened as Draft in session `2026-08-22-architecture-1`, from the findings of session
  `2026-08-21-investigation-2` and the three notes it promotes.
