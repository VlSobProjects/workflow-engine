# ADR 016: Reference interpolation in text

## Status
Draft

## Active branch
—

## Context

A `param.` / `output.` / `artifact.` reference resolves only as a whole configuration value
(`StateModel._resolve_reference`): a string that *is* a reference becomes the value, a string that
*contains* one stays literal. The `ask` presentation fields pass through the same resolution
(`_resolve_text`), so a question can show one state value per field — as the whole field — and never
inside a sentence.

The ADR-0083 investigation (session `2026-08-20-investigation-1`) measured what that costs. In the
eleven-node flow, **three of the four questions had to show a prior value as a bare `context` field**
because it could not be written into the sentence, and each instruction had to be bent around it —
"the folder named below", "the issues below". Only the first question, which needs no prior state,
escaped. A list shown this way reached the answerer as a Python repr (`"['a', 'b']"`), because
`render_value_as_text` falls back to `str()` for anything that is not a string or a path. The
load-bearing scenario of the external `loop-start` node — "here is the draft I produced, do you
approve?" — is exactly the case the count describes (coverage note, friction 1).

The gap is an asymmetry, not a missing luxury. The automatic side declares what it needs from the
state in `function_parameters`, and the engine resolves the values before the function runs. The
interactive side has no equivalent, because its consumer is not code but a reader: the analogous
mechanism is resolution *inside the text*. ADR 015 §1 deliberately deferred pre-processing of the
question in favour of this decision — most of what a pre-function would do is "assemble the question
text from state", which interpolation does declaratively — and ADR 014 open point 1 waits on the same
answer for the prompt of an `llm` node.

Constraints:
- ADR 013 §6: a plain `resume` re-presents the question and must not execute code. Interpolation is
  engine resolution — a pure function of the state, the same kind `_resolve_text` already performs on
  every re-present — so re-presenting keeps running no user code.
- The question's values are shown outward, so they must pass the disclosure boundary: only what the
  node declares reaches the presentation, the block and the journal. Interpolation is declaration —
  the reference is written in the workflow file, visible in review.
- ADR 008: a path renders in POSIX form on every surface.
- ADR 012 deferred §1 keeps whole-value resolution shallow; this ADR must not silently widen it.

## Decision

### 1. References resolve inside text, in fields declared as templates

A text field that is declared *template text* may contain `${param.<name>}`, `${output.<name>}` and
`${artifact.<name>}`; the engine replaces each with the referenced value, rendered as text, when the
field is resolved. `$$` escapes a literal `$`. A whole-field reference (today's form) keeps working
unchanged: a template field whose entire value is a bare reference resolves exactly as before.

Templating is a property of the **declared field, not of strings in general**. The component's
operator documentation declares which fields are template text (the ADR 009 surface carries the
kind), starting with `instruction` and `context` of `ask`; the prompt of the ADR 014 `llm` node joins
when that ADR lands. Every other string in every configuration keeps its exact meaning — a literal
`${` in a function parameter, a script body or a written file is not touched. This is what makes the
mechanism safe to add: nothing changes semantics silently.

### 2. An unresolved reference is a node error

A reference to a missing parameter, output or artifact fails the node with the same error class that
whole-value resolution raises today. It does not pass through as a literal: a typo in a parameter
name must not reach the published surface as `${param.rooot}` — the far end would answer a broken
question, and the flaw would surface two nodes later as a wrong answer instead of here as an error.

### 3. One rendering rule, extended to collections

`render_value_as_text` stays the single rule for how a state value becomes text on every surface — a
guard comparison, an output text, a presentation — and gains a case: a **list or dict renders as
compact JSON**, produced with the same encoder the state serialization uses, so a `Path` inside a
collection renders in POSIX form and a `datetime` in ISO form, exactly as they are stored. A string
renders as itself, a path in POSIX form (ADR 008), and any other scalar via `str()`, all unchanged.

This replaces the Python repr on the published surface (`["a", "b"]` instead of `"['a', 'b']"`) — a
language-neutral form an agent can parse and a human can read — and it applies to the bare `context`
field as well, independently of whether the field uses a template.

### 4. Resolution is engine resolution, at presentation time

The values are resolved when the presentation is built, from the same state view every resolution
uses. A re-presented question re-resolves and shows the same values, because the state does not
change while the run is paused; no user code runs (ADR 013 §6 holds). The rendered text lands in the
presentation and therefore in the published question block and the journal: what the answerer was
shown is exactly what the run recorded.

## Alternatives considered

### A. Keep whole-value references and composing nodes
The status quo: a value is shown as a bare field, or a node composes the sentence into a parameter
that the presentation references. Free, and every step stays in the journal. Rejected by the count:
three of four questions paid the bare-field cost, the composing node is the same data-only node class
that ADR 015 just removed on the answer side — keeping it mandatory on the question side is the same
gap under another name.

### B. A composing registered function before the question
A `format_text` function node, or a pre-function on `ask`. The node form is alternative A with a
name. The pre-function form was already deferred by ADR 015 §1: it collides with ADR 013 §6, because
re-presenting would execute code, and interpolation does the same job declaratively. Nothing here
changes that judgement — it confirms it, since the count shows no case interpolation cannot express.

### C. Template resolution in every string
Make every string in every configuration a template. Uniform, no field declaration needed. Rejected:
a literal `${` in a function parameter — a shell snippet, a regex, file content — silently changes
meaning, and the blast radius is every workflow ever written. The declared-field form keeps the
mechanism where the evidence is and leaves every other string alone.

### D. Deep resolution into containers
The other branch of ADR 012 deferred §1: recurse whole-value resolution into nested lists and dicts.
Orthogonal — it still cannot put a value inside a sentence, and this ADR does not need it. Deferred
§1 stays open and is narrowed only this far: references inside text exist for declared template
fields; whole-value resolution stays shallow everywhere.

### E. A declared context map
`context` as a mapping of named references (`{folder: "param.root", issues: "param.issues"}`),
published as structured named fields in the question block — the structural twin of interpolation,
and a renderer would like named fields. Not taken: no question in the flow needed more than one
value, so there is no evidence yet. Additive when it comes; revisit when a flow shows a question
needing several structured values, or when the rendering note's ADR wants them.

### F. Full context at presentation time
Give the presentation stage the state — a pre-function, a processor generating the instruction, or a
state view embedded in the published block. Rejected in three forms in the same week (ADR 015 §1, and
the question-rendering note): re-presenting would run code or diverge from the journal, the answerer
would see past the disclosure boundary, and the question's content would stop being readable from the
workflow definition. Interpolation is the declared subset of the same power: the state reaches the
question only through references written in the node.

## Consequences

- Enables: a question that carries its values inside the sentence; the ADR 014 prompt mechanism
  (open point 1 of that ADR is decided by this one for the in-text case); a defined rendering for
  collections on every text surface, replacing the Python repr on the published block.
- Absorbs most of the motivation for pre-processing an interactive node: ADR 015 left it open
  pending this decision, and what remains open there is only the case where a question must be
  *computed* rather than composed — for which no evidence exists yet.
- Costs: a template scanner and an escape rule; the template-text kind in the operator help surface
  (ADR 009); and a behavior change on comparing surfaces — a guard that compares the text of a
  collection sees compact JSON where it saw a Python repr, to be checked against the suite at
  implementation time.
- Closes off: nothing. Whole-field references keep working; non-template strings keep their exact
  meaning.
- Leaves open: deep container resolution (ADR 012 deferred §1), the declared context map
  (alternative E), and widening the rendering rule to codec forms for the remaining scalars
  (`bool`, `datetime` outside collections), which would change comparing surfaces and has no
  evidence behind it.

## Related ADRs

- Depends on: ADR 006 (the state and codec contract the values come from), ADR 008 (POSIX rendering),
  ADR 012 (the reference forms and the inputs they resolve against), ADR 013 (the presentation fields
  this templates), ADR 009 (the help surface that declares a field template text).
- Touches: ADR 014 (open point 1, decided for the in-text case), ADR 015 (pre-processing stays out,
  now with its main use absorbed).
- Supersedes: nothing.

## Implementation notes

No POC. The mechanics are known: `string.Template` from the standard library implements exactly
`${...}` with `$$` escaping and accepts a custom identifier pattern that admits the dotted reference
form, so no parser is written and no dependency is added. The substitution values pass through
`render_value_as_text`; the collection case reuses `common_encoder`, which already renders `Path` as
POSIX and `datetime` as ISO inside serialized state. The declared-field kind extends
`ActionParameterDoc`. The suite must be checked for guards comparing collection text, which change
from repr to JSON.

Open points to settle before leaving Draft:

1. Whether `title` and `description` of `ask` are template fields from the start or join later; both
   are additive either way.
2. Whether the unresolved-reference error is the existing resolution error class verbatim or carries
   its own error code so a transition can route on it; the precedent is that resolution failures are
   setup-shaped errors, not routable ones.

## Change log

- 2026-08-20: opened as Draft in session `2026-08-20-architecture-3`, from the count the ADR-0083
  investigation produced (three of four questions showing a value as a bare field) and the rendering
  fact that came with it (a list published as a Python repr). The session also fixed the boundary
  against the neighbouring temptations: rendering the block for an audience is a separate concern
  (question-rendering note), and full context at presentation time is rejected in all three forms
  (alternative F).
