# The workflow that authors a workflow

- **Identifier:** `workflow-authoring`
- **Class:** `2`
- **Answerers:** one answerer for every step, in two named variants of one definition. Variant
  `human-direct`: the human answers the engine directly through `resume --answer` and sets every
  parameter of every node themselves; the published block is the whole surface they act from.
  Variant `agent`: an agent takes the client's semantic explanation of a step — "then check that
  the folder exists and stop if it does not" — and composes the node definition itself, asking the
  client only what the explanation leaves open. Nothing in the graph encodes which variant is
  running — the engine never knows who answers.
- **Input data:** the fixed data is the engine's own: the component catalog that
  `help-components` / `help-component` publish — descriptions, parameter docs and examples
  (ADR 007, ADR 009), serving the human and the agent alike — and the definition format a session
  loads. The target workflow is arbitrary and its authoring intent is live dialogue, not prepared,
  the way the interview of `repository-interview` is live.
- **Expected paths:** the straight growth path — setup, then one node per pass of the authoring
  cycle until the author declares the graph complete; the clarification loop under `need_more_data`
  inside a pass; the review detour showing the node under construction and the draft so far;
  validation on demand after any pass, its errors routed back as repair passes; the continuation
  after the answerer is lost or replaced, in both variants; walking away as a declared failure
  answer. Details in the body.
- **Ends with:** end of workflow with the created definition written to disk, validated — the
  definition loads, every name resolves, the graph builds, without executing a node — and exported
  as a deliverable together with the validation evidence; the first run of the created workflow is
  its own session and lies outside this scenario. Failure under `max_visits_exceeded` when repair
  exhausts its bound, or under the declared failure answer code `authoring_abandoned`; every
  question in between is an ordinary pause.
- **ADRs exercised:** ADR 007, ADR 009, ADR 011, ADR 012, ADR 013, ADR 015, ADR 016, ADR 017,
  ADR 018

## The consumer

The done condition of `docs/architecture/purpose.md` ends with the authoring claim — an author who
knows the domain but not the engine — and phase 3 gates it in its assisted form, with the
blind-agent experiment over the `agent` variant as the phase exit. This scenario mechanizes that
claim for any target workflow: the engine knowledge — which components exist, what a transition
needs, what a guard may read — lives inside the authoring workflow as its questions and its checks,
so the author brings only the intent. The `agent` variant serves the consuming project of
`repository-interview`: an agent that scaffolds a repository will next need workflows for it, and
authoring them is the same cycle with the client explaining steps semantically. The scenario is
also the engine's own proof: a workflow that assembles a valid workflow through the published
contracts demonstrates that those contracts are complete enough to be operated blind.

## Everything this scenario needs is core work

The components this scenario lacks ship in the core, none beside the scenario as an external
module — the opposite placement from `repository-interview`, whose consumer formats stay outside.
The rule that decides: shape every function as the most universal form that still does the job —
dict and list assembly, writing a composed document, surfacing check results as data are bus work
any workflow can reuse — and where a component is specific to this scenario, it is specific to the
engine's own definition format, and the engine's knowledge of its own format belongs in the core,
not in a module a consumer must fetch to build workflows.

## The authoring shape

One universal cycle, not a flow per target:

- **Setup** — the target's name and description; an empty definition begins on the bus. Then the
  start parameters of the target, each typed by a registered codec.
- **The node cycle** — the heart of the flow. One pass adds one node, and the cycle's questions
  must reach every configuration option a node has: the action and its configuration, the parameter
  writes, the `validators` sugar where a plain refusal is meant, the guarded transitions and
  failure routes, and the interactive fields when the node being authored is an `ask`. In the
  `human-direct` variant every one of these is a question the human answers; in the `agent` variant
  the agent fills them from the client's explanation and asks only for what it lacks. The catalog
  surfaces of ADR 009 feed the choices: the instruction text points the answerer at
  `help-components` / `help-component`, whose examples serve the human and the agent alike.
- **Review** — at any point of a pass the author can ask to see the node under construction and
  the draft assembled so far, rendered as the definition it will become, before committing the
  pass.
- **The per-pass choice** — every pass ends with one decision: add another node, review the draft,
  validate what exists so far, or declare the graph complete. Routing rides on the surfaced answer.
- **Validation** — code, never the model: the definition on disk loads, every named component
  resolves against the registries, every transition target exists, the graph builds — a session
  initialization that executes nothing. The errors come back as data the flow presents, and each
  one routes a repair pass back into the cycle at the piece that caused it.
- **Progress and continuation** — the authoring must survive the loss of its answerer in both
  variants: a human returns after a break, an agent's context is wiped or another agent takes
  over. The returning answerer needs the current progress — the draft definition, the position in
  the cycle, and, in the `agent` variant, the questions asked and the answers given — without
  reading the engine's mechanics. What the author wants is effectively a progress view reachable
  from any point of the flow; what mechanism serves it is open decision 7.
- **Handover** — the definition and the validation evidence exported as deliverables (ADR 011);
  running the target is the target's own first session.

Two different bounds keep the two loops honest: the growth loop is bounded by a declared size cap
on the accumulating node list — `max_visits` cannot bound it, or the cap on the authoring nodes
would cap the size of every workflow authored — while the repair loop after a validation refusal is
bounded by `max_visits` (ADR 017), and a question re-asked in place by `max_attempts`.

## Expected paths

1. **Straight growth.** Setup, then one pass per node; the author declares the graph complete; the
   final validation passes at the first attempt; the definition and the evidence export.
2. **Clarification.** An answer inside a pass does not suffice; `need_more_data` re-presents the
   question, bounded by `max_attempts` — the engine re-asking the human in `human-direct`, the
   agent asking the client first in `agent`.
3. **Review.** Mid-pass the author asks to see the node under construction or the draft so far;
   the flow shows the rendered definition and returns to where the question left off.
4. **Validate early.** After a pass the author chooses validation mid-build; the errors of the
   half-built graph that are expected at that point — transitions into nodes not yet added — must
   be distinguishable from real defects; the author repairs or continues growing.
5. **Repair.** The final validation refuses — an action name that resolves to nothing, a
   transition target that does not exist. The refusal routes a repair pass to the offending node;
   the re-entry counts against `max_visits`, and exhaustion fails the run under
   `max_visits_exceeded`.
6. **Continuation.** The run pauses mid-build and the answerer is gone — the human comes back days
   later, or a fresh agent replaces the one whose context was lost. The returning answerer pulls
   the progress — the draft, the position, in the `agent` variant the exchange so far — resumes
   the paused question and continues as if never interrupted.
7. **Walk-away.** The author abandons; the declared failure answer fails the run under
   `authoring_abandoned`.

## Open decisions the scenario lacks

1. **The catalog is served outside the run.** `help-components` / `help-component` already publish
   the component list with descriptions, parameter docs and examples (ADR 007, ADR 009), and the
   answerer of either variant operates the CLI anyway, so the instruction text can point at them.
   Open is only whether pointing suffices or the question block should carry the relevant catalog
   slice; the wider authoring surfaces — `validate`, `describe-workflow` — remain gap G11
   (`2026-08-23-architecture-1` §2), and this scenario is their second consumer.
2. **No validation without a run.** The check this scenario ends with — load, resolve, build,
   execute nothing — has no surface: today the only initialization is the one that starts running.
   And the scenario needs the refusal as data — a structured error list the flow can present and
   route on — not as a process exit code. G11's `validate`, consumed from inside a workflow.
3. **No base document write for a collection.** The assembled definition is a value on the bus;
   ADR 020 ships the base text write for a string and refuses anything else, so writing the
   definition itself is the part it left open with this scenario as the trigger — the remainder of
   what `repository-interview` open decision 4 named, and the live remainder of G6 here.
4. **No dict and list assembly beyond append.** Composing a node definition, setting keys on the
   growing document, and above all repair — replacing node N inside the accumulated list — have no
   core functions: nothing creates or sets a dictionary parameter and the only list operation is
   `append_to_param` (gap G5, widened by the repair need).
5. **A structured answer's keys are unchecked.** A node definition collected as `type: dict`
   accepts any dictionary (gap G4); without the check the damage surfaces late, at validation,
   instead of at the answer that caused it.
6. **The block never states the answer's form.** Shared with `repository-interview` open
   decision 2 and most acute in the `human-direct` variant, where no agent softens the surface: a
   human asked for a guard configuration needs the declared shape, not prose. ADR 019 territory.
7. **A detour has no return address.** Review and progress want a node reachable from any point
   that comes back to where the flow was, and transitions are static targets — the engine has no
   return-to-origin. The candidates: the published block itself carries the digest of the draft
   (ADR 019 territory); the ADR 018 read surfaces plus an author-accumulated record serve it
   outside the run, as `repository-interview` open decision 6 already asks for the exchange; or
   every question routes to the review node explicitly, which multiplies transitions the way
   gap G7 warns about. Which mechanism the scenario gets is open.
8. **Mid-build validation needs a tolerance.** Path 4 validates a graph that is legitimately
   incomplete; a validator with one notion of correctness refuses every half-built graph and makes
   the per-pass validation useless. Whether the check takes a mode, or the flow filters the error
   list, is open.
