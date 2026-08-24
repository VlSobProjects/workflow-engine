# ADR 020: Output composition functions

## Status
Draft

## Active branch
—

## Context

The operator of the shipped scenarios reported the output surface as the weak one
(`docs/architecture/notes/2026-08-24-result-file-composition.md`): the inventory examples export
one flat table over every file of the walked tree, which a human practically cannot read. The
wanted shape is a composed document — one table per folder, the folder path as its heading — not a
bigger table.

What the core renders today is one table shape in six syntaxes (`dict_list_to_pretty_table`);
file functions copy and delete but none writes a composed string; template text is confined by
ADR 016 §1a to the ten presentation fields of `ask`. Four scenarios hit this same wall
independently:

- `folder-inventory-to-csv` (class 4): the flat table the operator reported.
- `load-test-triage` (class 2, phase exit): the triage report and the handover are composed
  documents (open decision 4), and its `llm` nodes produce text that must land in an artifact.
- `repository-interview` (class 2): the final document of the demonstration ending cannot be
  written — "no base text write" (open decision 4).
- `2026-08-21-support-intake-use-case`: the handover is not a table (gap 3).

Every new output form today is one more hardcoded function — the note asks what stops the next
format from being the seventh syntax.

Constraints:
- ADR 006/011: artifacts live under `work_dir/artifacts`, functions register what they write,
  export is an explicit copy. Unchanged.
- ADR 016: templating is a property of a declared surface, the braced `${...}` form only, two
  failure classes at two times. This ADR extends the declared set — a growth ADR 016 §1a
  anticipated — and must not widen resolution semantics silently.
- ADR 008: paths render in POSIX form on every surface.
- ADR 004: a resumed session builds from its own record, not from the current environment.

## Consumer

The party that acts on the delivered surface is the human who reads the exported result — the
operator of the inventory examples, the load-testing analyst receiving the triage report or the
handover — and, for a composed prompt artifact, the next model or external agent that reads it.
The scenarios served: `load-test-triage` (the report and the handover of open decision 4;
the verbatim text writer is also how its `llm` nodes persist composed text) and
`repository-interview` (the final document of open decision 4); both list this ADR in the same
session. The freeze evidence is class 4 and small: the `folder-inventory-to-csv` walkthrough
corrected to the grouped output the operator asked for, with the e2e tests exercising the new
functions; the walkthrough and the scenario registry list this ADR when the feature branch merges
(the ADR 014 precedent).

## Decision

Output composition stays in registered functions. No document model, no renderer registry: the
core ships a small family of output functions, each admitted by a need a scenario names, plus one
mechanism — a template file rendered through the existing ADR 016 resolution into an artifact.

### 1. The family ships three functions

- **A grouped-table writer.** Takes a list of dictionaries, a grouping key, an artifact name, a
  relative path and the existing `table_format`. It writes one composed document: per group, in
  sorted group-key order — a heading line carrying the group value (POSIX form for paths, ADR
  008), an empty line, then the group's rows as a table in the requested format; an empty line
  between sections. The grouping column is the heading, so it is dropped from the rows. The table
  syntax inside a section is any of the six existing formats; the composed file as a whole is a
  document for a reader, not a machine-parseable single table, and that is its purpose.
- **A verbatim text writer** — `write_text_artifact(text, artifact_name, relative_path)`. Writes
  a string value as-is and registers the artifact. This is the base text write three scenarios
  ask for, and the way an `llm` node's composed reply becomes an artifact in whatever format the
  model was instructed to produce: from the engine's side it is bytes of text, format-blind.
- **A template renderer** — takes a template file, an artifact name and a relative path; renders
  the file's content through ADR 016 `${...}` resolution against the run's state and writes the
  result as the artifact. For the simple composed document — a report whose shape needs values in
  sentences but no iteration — and for the prompt one model or an external agent authors for
  another.

### 2. Template text outside `ask`: exactly one new surface

The template file's content joins the declared template-text set of ADR 016. The declaration rule
of ADR 016 §1 holds unchanged: templating stays a property of a declared surface an author can
see, and the component documentation (ADR 009 surface) carries the kind. The two failure classes
of ADR 016 §2 apply at the same two times: a malformed template is a configuration error of the
node, found when the template is loaded at build time and aggregated with the other configuration
errors (ADR 001); an unresolved reference is a runtime error at rendering and fails the run at
that node, exactly as whole-value resolution fails today.

Template text comes only from authored surfaces — a declared definition field or an authored
template file. A run value is data: a `${` inside a parameter value, a model reply or a file a
function read stays literal and is never resolved. This keeps the ADR 016 review property — every
reference that can reach a surface is written in reviewable, authored material.

### 3. The template file and its loading

- The template path is a configuration value of the node: an absolute path is used as-is, a
  relative path resolves against the directory of the workflow definition file. The operator does
  not compute relative paths to a template that lives elsewhere.
- The template is read and syntax-checked at build time, before anything runs.
- At session start the template file is snapshotted into the session directory beside
  `workflow.json`; a resumed session reads the snapshot, not the original path (ADR 004: resume
  builds from the session's own record, so a template edited or moved mid-run cannot change a
  paused workflow).
- This loader is the single template-file loader: the `prompt_ref` of ADR 014 and the
  `instruction_file` of ADR 019 are recorded in those Drafts as its next instances. The mechanism
  is born here with one instance.

### 4. Templates substitute; functions iterate

A template resolves `${param.}`/`${output.}`/`${artifact.}` references and nothing else: no
loops, no conditionals, no template language. Where output needs iteration or grouping — a table
per folder, a section per finding — that shape is a registered function, reviewable as code. This
line is what stops format sediment on the template side, and the admission rule — a new output
function enters the core only for a need a scenario names — is what stops it on the function
side.

## Alternatives considered

### A. A document model: author-declared shapes rendered by the engine
A `document` artifact declared in configuration — sections, groupings, per-section sources —
rendered by a registry of renderers.

Pros: one declarative mechanism could express every composed output; no new function per shape.
Cons: the widest surface by far — a schema, a renderer registry, a nesting model — and no phase 2
scenario needs more than grouped tables, verbatim text and value substitution; the declaration
language would itself grow loops and conditionals, a template language by another name. Rejected
as not paid for by any named consumer; a later scenario that needs nesting reopens it with
evidence.

### B. Two ADRs: the template mechanism and the output functions separately
Template text outside `ask` as one decision, the function family as another.

Pros: cleaner rule 3 reading; the mechanism also serves the ADR 014 prompt.
Cons: the mechanism's only phase 2 consumer is this family — the `llm` prompt takes it later
through the shared-mechanism records of ADR 014 §7 — so the mechanism ADR alone would name no
consumer able to act on it (rule 11), and the pair would be implemented together anyway. One
decision — output is composed from run values through declared, authored surfaces — with three
consequences, not three decisions. Rejected.

### C. Component work only, no ADR
Write the three functions; functions need no ADR.

Pros: cheapest path; the grouped-table writer is indeed writable today.
Cons: the template renderer extends the declared template set of an accepted ADR (016), builds
the loader two Drafts (014, 019) wait on, and sets the substitute-don't-iterate boundary — those
are decisions, not components; leaving them undocumented is how the six-syntax sediment happened.
Rejected.

### D. A template language with iteration
Adopt or build a template engine (loops, conditionals) so grouped output is a template too.

Pros: one mechanism covers the grouped case; no grouped-table function needed.
Cons: an external dependency (rule: minimal dependencies) or a homegrown language; control flow
moves from reviewable code into template files; the ADR 016 property — resolution is a pure
engine function over declared references — is lost. Rejected; §4 closes this off deliberately.

## Consequences

Enables:
- The inventory examples export the document the operator asked for: a table per folder under its
  path heading.
- Any composed string a node produced — a model reply above all — becomes an artifact and a
  declared deliverable (ADR 011) in whatever format it was authored.
- A simple report or a prompt for the next model is an authored template file plus one node.
- The e2e tests and the shipped examples exercise the family immediately at implementation.

Costs:
- Three functions with full ADR 009 documentation and tests.
- The template loader with its build-time check and session snapshot step.
- The declared template-text set is no longer enumerable from `ask` alone; the component
  documentation carries it (as ADR 016 already provides).

Closes off:
- Iteration and conditionals in template text — permanently; shapes are functions (§4).
- Resolving template syntax found in run values — a `${` in data stays literal (§2).
- New core output functions without a scenario-named need (§1, §4).

Leaves open, with triggers:
- **Template text in function parameters generally** — composed artifact names such as
  `${param.ticket}_intake_table` (`support-intake` gap 2). Trigger: the reformatting of
  `support-intake` into a class 2 scenario beside the ADR 019 narrowing (roadmap step 11).
- **A readable JSON dump of a bus value** (the assembled definition of `workflow-authoring`, gap
  3 — the verbatim text writer takes a string, not a dictionary). Trigger: building the
  `workflow-authoring` scenario.

## Related ADRs

- ADR 006 (Accepted): the bus and artifact registration contract the functions write through.
- ADR 011 (Accepted): artifact addressing, deliverables and export the outputs flow into.
- ADR 016 (Accepted): the resolution mechanism and failure classes §2 extends; its §1a
  anticipated the declared set growing by ADR.
- ADR 004 (Accepted): the session-snapshot principle the template snapshot follows.
- ADR 005 (Accepted), ADR 008 (Accepted): registration and path form.
- ADR 014, ADR 019 (Drafts): record the template-file loader of §3 as a shared mechanism they
  reuse; nothing here constrains them.

## Implementation notes

- Grouped writer: group-key order is the sort order of the rendered key values; a row missing the
  grouping key is a function error (strict pre-check, ADR 006 style), error codes mirroring the
  pretty-table family (`no_data`, `artifact_exists`, `write_error` naming). UTF-8, LF newlines.
- Verbatim writer: accepts a string; any other type is a function error — the collection dump
  stays a leaves-open item, not a silent coercion.
- Template rendering is engine resolution (ADR 016 §4) over the loaded content; the function
  receives the rendered text, so the write path of the verbatim writer is shared.
- Snapshot: copy the resolved template file under the session directory at session creation;
  record the snapshot path in `session.json`; resume loads the snapshot. A missing template file
  at session creation is a setup error (exit code 4 family), not a run failure.
- Test surface: unit per function (grouping, ordering, dropped key column, strict type check,
  overwrite refusal); build-time malformed-template aggregation; unresolved-reference failure at
  the node; snapshot-resume (template edited after start, run unaffected); e2e: the corrected
  grouped inventory walkthrough with export.

## Change log

- Draft opened in session `2026-08-24-architecture-2` from the operator's report
  (`2026-08-24-result-file-composition` note), executing roadmap step 7. Rule 3 checked: one
  decision (composition through declared authored surfaces) with three shipped functions; the
  document model and the two-ADR split recorded as rejected alternatives. The grouped-table
  format kept open to all six syntaxes and the absolute template path admitted, both on the
  owner's direction; the session snapshot of the template added for resume hermeticity.
