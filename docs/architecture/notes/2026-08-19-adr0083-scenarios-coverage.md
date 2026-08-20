# Can this engine carry the ADR-0083 questionnaire scenarios?

- **Date:** 2026-08-19
- **Trigger:** question raised while preparing ADR 013 for implementation (session
  `2026-08-19-architecture-2`): ADR-0083 of the external `java-claude-ai` repository — a
  JSON-configured questionnaire engine with a six-type node graph — is where this project started
  before it went its own way. Can its *scenarios* (not its contract) be realized here once ADR 013
  ships, given some external registered functions?
- **Status:** open
- **Affected:** ADR 010 (budget checkpoint shape, and now a per-node visit cap), ADR 012 (deferred §1,
  shallow reference resolution), ADR 013 (Accepted and delivered; the table below was re-verified
  against the code — see "What the implementation changed"), ADR 014 (Draft; its open point 1 is
  decided by ADR 016 for the in-text case), ADR 015 (Draft; the run below is the evidence its open
  points were waiting for, settled in session `2026-08-20-architecture-2`), ADR 016 (Draft, decides
  text interpolation — friction 1 below)

The answer is yes for the substance, with one core gap, one shape difference, and one function to
write. Recorded here because the mapping keeps being re-derived, and because two of the three
frictions belong to decisions that are still open.

This note is the yardstick for the first goal of phase 2: reaching a state where these scenarios can
actually be run and checked, not argued about. It was first written while ADR 013 was still
`Implementing` and no code existed; the table has since been re-verified against the delivered engine.

## What ADR-0083 asks for, and what carries it here

| ADR-0083 | Carried by | Verdict |
| --- | --- | --- |
| `Q` — one prepared question to the operator | `ask` node: text and options in the presentation, a typed `answer` entry; `input_mode` is expressed by the codec (`path` → `pathlib.Path`) | full for asking and binding; the node cannot check what it bound — see "What building it found" |
| `A` — agent branch decision, no dialogue | the same `ask` node, answered by an agent; `allowed_values` is an `any_of` of `equals` guards **over the answer text**; `default` with `require_reason` is a `failure` answer with a code and a message; `auto_log_stop` is a `FailTarget` plus the `interactive_answered` event | full when the decision travels in `text`; a decision that travels as a declared value needs an `echo_value` node in front of the guards |
| `I` — instruction to the agent to act and report | the same `ask` node: the presentation is the instruction, the agent acts outside the engine and answers with the aggregated result; node `validators` already exist | full |
| `S` — deterministic script with parameters | a `function` node over an external registered function that runs the script; `script_output_match` is several transitions with `contains` guards, whose configured value resolves `param.` references | needs one external function |
| `STOP` | `stop` / `stop_on_error` and the `EndTarget` / `FailTarget` transition targets; `handoff_ref` is a deliverable (ADR 011); `cleanup_scripts` is a node before the end | full |
| `FQ` — up to N agent-generated questions | a loop `CHECK → ask → COLLECT → CHECK`: `append_to_param` accumulates each answer and the `is_collection_size_at_least` guard on the head node leaves the loop once there are enough. A question repeated in place instead, without collecting, is bounded by `attempts` | full, at the cost of two nodes around the question; covered end to end by `tests/test_bounded_accumulating_loop.py` |
| typed validators (`non_empty`, `regex`, `enum`, `path_exists`) | node `validators`, value guards, function guards | full |
| `attempt_counters`, `max_visits`, retry actions | `attempt_counters` / `max_attempts` for the retries; `visit_counters` is counted per node but never read, and the field is not on `StateReadOnlyView` | partial: retries are carried, `max_visits` is not — a loop is bounded by what it collects or by the global hard cap (ADR 010), not per node |
| logging: engine-authored vs agent-authored fields per node | `session_events` (the engine/operator actor split), `guard_results`, `outputs`, `errors`; the agent's verbal part is the answer's `text` and `message` | in substance, but the verbal part lives in the state, not in the journal: the journal deliberately never stores values |
| `recommended_answer` | presentation fields (`options`, `examples`, `hints`, `context`) | full |
| persistence `set` / `append`, artifacts vs structured facts | `WriteParamMode.SET` / `APPEND`, `state.params` for facts, artifacts and deliverables for documents (ADR 011) | the result is the same; the stance is the opposite — see below |

## What the implementation changed

Re-verified against the delivered engine after ADR 013 was accepted and three defects around it were
fixed. The mapping held; three cells did not.

1. **`input_mode: path` was true in the model and false in execution.** A value declared `type: Path`
   arrives as a `pathlib.Path` — and until session `2026-08-19-implementation-12` no file function
   accepted one: the argument validators demanded a `str`. Until `-14` its comparison in a guard was
   broken on Windows as well, which is exactly what `script_output_match` does in row `S`. Both are
   fixed; the row is now true end to end.
2. **A value guard reads the answer text, never a declared value.** `equals`/`contains` compare
   `output.output_text`, resolving `param.` inside the *configured* value. So `allowed_values` works
   directly when the decision travels in the answer's `text`, and a decision bound as a declared value
   has to be surfaced into a node output first — the documented `echo_value` pattern — or compared by
   a registered validator that takes both sides as arguments. Neither is a gap; it is a choice the
   author has to make knowingly, and the original row hid it.
3. **`FQ` is better and worse than recorded.** Better: a question repeated in place needs no self-loop
   that fails at the end — a transition carrying `attempts` re-presents it while attempts remain and
   then routes on gracefully. Worse: that bound does not survive a loop that collects, because leaving
   the node resets the attempt counter, and an answer writes `SET` only, so the count has to come from
   what was collected.

   Closed in session `2026-08-19-implementation-15` by two small components rather than by a change of
   semantics: `append_to_param` (the accumulating half the collection family was missing next to
   `init_list_param`) and the `is_collection_size_at_least` guard, which reads the resolved collection
   because a function guard's arguments are resolved from the state.

   Building it taught the third thing, which is general and was not written down anywhere: **a guard
   sees the state as it was before its own node wrote to it.** The engine selects the transition and
   only then applies the node's writes, so the size check cannot live on the node that appends — it
   belongs at the head of the loop, on a node that runs after the write has landed. The working shape
   is `CHECK → ask → COLLECT → CHECK`, which is exactly the two extra nodes the "more verbose" verdict
   predicted. The rule is now stated in the guards section of the architecture overview.

Also confirmed while re-verifying: a `list`-typed answer value binds as a real Python list of
dictionaries, so the one-node form of `FQ` (the agent returns all question/answer pairs at once) needs
nothing beyond the core. And the node error catalogue plus the generic `answer_failed` covers the
per-node error taxonomy of ADR-0083, which the first version of this note did not call out.

## What building it found

Written and run in session `2026-08-20-investigation-1`. The mapping above survived: every ADR-0083
node type the flow covers is reachable, the run completes, and the handoff leaves the session as a real
exported deliverable. Four things the table could not have known, all of them about the `ask` node.

1. **The node that asks cannot check what it bound.** A `validators` entry and a transition guard both
   read the node's output, and an answered value is not in the output text — it is in `param_writes`,
   which the bus applies only after the transition has been selected. So a typed answer is checked one
   node later, by a node that surfaces it. That node is not decoration: without it a declared `Path`
   answer is bound and used unverified.

2. **The retry that follows is unbounded.** Sending the check back to the question re-enters it as a
   fresh *visit*, and `attempt_counters` is reset on every departure, so `max_attempts` never counts up.
   The flow's own test gives the same wrong answer five times and the question keeps coming back;
   nothing bounds it but the global hard cap of ADR 010. This is the first concrete argument for a
   per-node visit cap, which until now had none — `visit_counters` is written and read by nobody.

3. **A re-presented question says nothing about why.** Both stalls the live run hit — a relative path,
   and a decision word with an explanation attached — returned the identical question block with an
   empty `errors` map. The answerer gets no signal that the previous answer was rejected and no reason,
   so an agent answers the same thing again. ADR 013 §6 defines re-presenting as consuming nothing; it
   does not say what the answerer is told, and the answer today is "nothing".

4. **The exactness of a decision is carried by the wording, not by the contract.** Four places in the
   flow had to constrain the answer in prose — the shape of a list element, "put nothing else in the
   answer text", the keys of a `dict`, and "answer with exactly 'approved' or 'rejected'". Two of the
   four were violated by the first natural answer a model gave. A `dict` codec has no key schema, so the
   columns of the exported handoff table rest entirely on a sentence in the instruction.

Also observed, smaller: a declared `Path` is published to the answerer as `pathlib._local.Path`, the
private CPython 3.13 module name, which is not a name an answerer can be expected to send back — the
same Python-version-dependent codec name recorded in `2026-08-18-adr012-deferred-questions.md`, now
visible in the caller-facing `question` block rather than only in the state.

## What is still missing, in order

The first goal of phase 2 is to run these scenarios for real. Nothing blocks that; this is the order
the work takes.

1. ~~`append_to_param` in the core.~~ Done in session `2026-08-19-implementation-15`, together with
   the `is_collection_size_at_least` guard the bound turned out to need.
2. ~~Build the scenario and run it.~~ Done in session `2026-08-20-investigation-1`:
   `tests/test_adr0083_scenario.py` is one workflow of eleven nodes covering `Q`, `A`, `I`, `FQ`,
   `STOP`, the counters, the `validators` and the error catalogue, run both by the scripted test and by
   an agent answering the published question blocks. It turned the remaining questions into evidence,
   as predicted — see "What building it found".
3. ~~Decide text interpolation.~~ Done in session `2026-08-20-architecture-3`: ADR 016 opened as
   Draft with the count of step 2 as its evidence — references resolve inside declared template
   fields, and collections render as compact JSON instead of a Python repr. Friction 1 below.
4. **The script-running function for `S`**, as an external module rather than a core component: it is
   a trust decision (friction 3), and shipping it outside the core exercises the ADR 005 external
   module path at the same time.

Not on this path, despite being next in the phase 2 plan: **ADR 014**. The agent-facing nodes of
ADR-0083 are answered through the interactive contract, which exists; the engine does not need to call
a model itself for these scenarios to work. The in-graph budget checkpoint (friction 2) is likewise a
fidelity question, not a blocking one.

## The simplification

`Q`, `A` and `I` are one node here. They differ only in who reads the presentation and what that
reader does before answering, and the engine is indifferent to both. That is exactly ADR 013 §1: the
answerer is a property of the answer, not of the node. ADR-0083 separates node types by *who
executes them*, which is why it needs six; this model needs three (`ask`, `function`, `stop`) plus
the transition targets.

## Where it rubs

1. **Interpolation inside text — the one real gap in the core.** `${answer.X}` inside a sentence does
   not resolve here: a reference is resolved as a whole configuration value, never as a template
   inside a string (ADR 012 deferred §1; ADR 014 open point 1). "Here is the draft I produced, do you
   approve?" therefore costs an extra node that composes the text into a parameter which the
   presentation then references. This is the load-bearing scenario of `loop-start`, so the templating
   question deserves to be decided rather than inherited.

   The count the decision was waiting for: in the eleven-node flow, **three of the four questions had to
   show a prior value as a field of its own** (`context`) because it could not be written into the
   sentence, and each instruction had to be bent around it — "the folder named below", "the issues
   below". Only the first question, which needs no prior state, escaped. A list shown this way also
   reaches the answerer as a Python repr (`"['a', 'b']"`), so what interpolation has to decide is not
   only where a reference may appear but how a non-string value renders once it is inside a sentence.
2. **The budget checkpoint is outside the graph.** ADR-0083 routes budget exhaustion to a declared
   node offering continue / summarize / finish, and "continue" raises the budget through a parameter.
   Here the run pauses (`workflow_paused_limit`, exit code 2) and the operator raises the limit with
   `set-limit` and resumes. The outcome is reachable — nothing is lost, deliverables can be exported,
   the limit can be raised — but the choice happens outside the graph, not in a node. An in-graph
   checkpoint would be a change to ADR 010, not to ADR 013.
3. **`S` is a trust decision, not an architectural one.** Running a script with resolved parameters is
   what ADR 005 external modules exist for. What it costs is a component that starts arbitrary
   processes on behalf of a workflow definition, which is a boundary question worth answering
   deliberately before such a function is written.

## Not a gap: caller-owned writes

ADR-0083 keeps its engine contract-pure — it returns write operations and the caller performs them.
This engine owns state and artifact persistence (ADR 003, ADR 006, ADR 011). The stances are
opposite, and the difference does not cost any scenario: what a flow needs to produce is produced
either way. It is recorded here only so the divergence is not mistaken for an oversight.
