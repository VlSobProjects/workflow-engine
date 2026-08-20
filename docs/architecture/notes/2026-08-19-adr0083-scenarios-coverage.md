# Can this engine carry the ADR-0083 questionnaire scenarios?

- **Date:** 2026-08-19
- **Trigger:** question raised while preparing ADR 013 for implementation (session
  `2026-08-19-architecture-2`): ADR-0083 of the external `java-claude-ai` repository — a
  JSON-configured questionnaire engine with a six-type node graph — is where this project started
  before it went its own way. Can its *scenarios* (not its contract) be realized here once ADR 013
  ships, given some external registered functions?
- **Status:** open
- **Affected:** ADR 010 (budget checkpoint shape; the per-node visit cap left it and became ADR 017),
  ADR 012 (deferred §1, shallow reference resolution — the in-text half of it is now decided by
  ADR 016), ADR 013 (Accepted and delivered), ADR 014 (Draft; its open point 1 is decided by ADR 016
  for the in-text case), ADR 015 (Accepted and delivered — computation on an accepted answer),
  ADR 016 (Accepted and delivered — text interpolation, friction 1 below), ADR 017 (Accepted and
  delivered — the per-node visit cap). The table below was re-verified against the code twice; see
  "What the implementation changed" and "What ADR 015, 016 and 017 changed"

The answer is yes for the substance. What was one core gap, one shape difference and one function to
write is now one shape difference and one function to write: the core gap — a value could not stand
inside a sentence — was closed by ADR 016. Recorded here because the mapping keeps being re-derived,
and because the two frictions that remain belong to decisions that are still open.

This note is the yardstick for the first goal of phase 2: reaching a state where these scenarios can
actually be run and checked, not argued about. It was first written while ADR 013 was still
`Implementing` and no code existed; the table has since been re-verified against the delivered engine
twice, most recently against ADR 015, ADR 016 and ADR 017 together.

## What ADR-0083 asks for, and what carries it here

| ADR-0083 | Carried by | Verdict |
| --- | --- | --- |
| `Q` — one prepared question to the operator | `ask` node: text and options in the presentation, a typed `answer` entry; `input_mode` is expressed by the codec (`path` → `pathlib.Path`). A prior value stands inside the question text as `${param.x}` (ADR 016) | full: since ADR 015 the node checks what it bound, because a post function reads the answered value and its result is what the node's own guards route on |
| `A` — agent branch decision, no dialogue | the same `ask` node, answered by an agent; `allowed_values` is an `any_of` of `equals` guards **over the answer text**; `default` with `require_reason` is a `failure` answer with a code and a message; `auto_log_stop` is a `FailTarget` plus the `interactive_answered` event | full: a decision in `text` routes directly, and one that travels as a declared value is surfaced by the node's own post function (ADR 015) instead of by an `echo_value` node in front of the guards. That function is `echo_answer`, and it ships in the core |
| `I` — instruction to the agent to act and report | the same `ask` node: the presentation is the instruction, the agent acts outside the engine and answers with the aggregated result; node `validators` already exist | full |
| `S` — deterministic script with parameters | a `function` node over an external registered function that runs the script; `script_output_match` is several transitions with `contains` guards, whose configured value resolves `param.` references | needs one external function |
| `STOP` | `stop` / `stop_on_error` and the `EndTarget` / `FailTarget` transition targets; `handoff_ref` is a deliverable (ADR 011); `cleanup_scripts` is a node before the end | full |
| `FQ` — up to N agent-generated questions | one `ask` node whose post function appends the answer and returns whether the loop has enough, so the node routes its own loop (ADR 015) — `collect_answer` in the core; the two-node form `CHECK → ask → COLLECT → CHECK` over `append_to_param` and `is_collection_size_at_least` still works and is what the core components alone can express. A question repeated in place is bounded by `max_attempts`, a loop that leaves and returns by `max_visits` (ADR 017) | full, and no longer at the cost of two nodes; the one-node form is covered by `tests/test_adr015_post_function.py`, the two-node form by `tests/test_bounded_accumulating_loop.py` |
| typed validators (`non_empty`, `regex`, `enum`, `path_exists`) | node `validators`, value guards, function guards | full |
| `attempt_counters`, `max_visits`, retry actions | `attempt_counters` / `max_attempts` bounds a question repeated in place; `visit_counters` is read by the engine on entry against the `max_visits` a node declares, and exhaustion fails the run under `max_visits_exceeded` before the action runs (ADR 017). Neither counter is on `StateReadOnlyView` | full for the bounds. What ADR-0083 spells as a retry *action* is still a transition here, and a guard cannot read either counter — the ordinals are journaled on `interactive_answered`, not exposed to the graph |
| logging: engine-authored vs agent-authored fields per node | `session_events` (the engine/operator actor split), `guard_results`, `outputs`, `errors`; the agent's verbal part is the answer's `text` and `message`. `interactive_answered` carries the visit and the attempt ordinal (ADR 017 §4) | in substance, but the verbal part lives in the state, not in the journal: the journal deliberately never stores values. The retries that the counters reset away are now readable from the journal itself |
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
   answer is bound and used unverified. — *Answered by ADR 015.*

2. **The retry that follows is unbounded.** Sending the check back to the question re-enters it as a
   fresh *visit*, and `attempt_counters` is reset on every departure, so `max_attempts` never counts up.
   The flow's own test gives the same wrong answer five times and the question keeps coming back;
   nothing bounds it but the global hard cap of ADR 010. This is the first concrete argument for a
   per-node visit cap, which until now had none — `visit_counters` is written and read by nobody.
   — *Answered by ADR 017; `visit_counters` now has its reader.*

3. **A re-presented question says nothing about why.** Both stalls the live run hit — a relative path,
   and a decision word with an explanation attached — returned the identical question block with an
   empty `errors` map. The answerer gets no signal that the previous answer was rejected and no reason,
   so an agent answers the same thing again. ADR 013 §6 defines re-presenting as consuming nothing; it
   does not say what the answerer is told, and the answer today is "nothing". — *Half answered: an
   author can now say why, ADR 013 §6 still says nothing on its own.*

4. **The exactness of a decision is carried by the wording, not by the contract.** Four places in the
   flow had to constrain the answer in prose — the shape of a list element, "put nothing else in the
   answer text", the keys of a `dict`, and "answer with exactly 'approved' or 'rejected'". Two of the
   four were violated by the first natural answer a model gave. A `dict` codec has no key schema, so the
   columns of the exported handoff table rest entirely on a sentence in the instruction. — *Softened by
   ADR 015: a post function can normalize a nearly-right answer and refuse a wrong shape, so the node
   no longer depends on the wording being obeyed. The `dict` codec still has no key schema.*

Also observed, smaller: a declared `Path` is published to the answerer as `pathlib._local.Path`, the
private CPython 3.13 module name, which is not a name an answerer can be expected to send back — the
same Python-version-dependent codec name recorded in `2026-08-18-adr012-deferred-questions.md`, now
visible in the caller-facing `question` block rather than only in the state. Unchanged by the three
decisions: ADR 016 decided how a *value* renders inside text, not how a codec names itself in the
answer declaration.

## What ADR 015, 016 and 017 changed

Re-measured in session `2026-08-20-investigation-2`, after the three decisions the findings above
produced were accepted and delivered. Each mechanism was checked in the code; the flow itself was not
rewritten, so the last item below separates what is verified from what is predicted.

1. **The node that asks can now check what it bound** (ADR 015). An `ask` node may carry
   `function_name`, and the engine runs that function on an accepted answer *before* the node's own
   transitions are selected. The function is handed the answer as the injected `output`, so it reads
   the answered value that has not reached the bus yet, and what it returns is the whole node output —
   the text the guards compare and the writes the engine applies. Finding 1 and the `echo_value`-in-front
   pattern of row `A` are both consequences of an ordering that no longer holds.

2. **A value can stand inside the sentence** (ADR 016). All ten presentation fields of `ask` are
   template text: `${param.x}`, `${output.NODE}` and `${artifact.name}` are replaced when the question
   is presented, a malformed template refuses the node at build time, an unresolved reference fails the
   run at the question, and a list or a dict renders as compact JSON instead of a Python repr. The count
   friction 1 was waiting for — three of four questions forced to show a prior value as a bare `context`
   field — is answered.

3. **A node bounds its own re-entry** (ADR 017). `max_visits` is checked on entry, before the action,
   so a question beyond the cap is never published; exhaustion fails the run under
   `max_visits_exceeded` and is not routable. Finding 2 is closed where it was measured: `ASK_ROOT` of
   the scenario declares `max_visits: 3` and the same wrong answer now ends at the question node
   instead of at the ADR 010 hard cap.

4. **The re-presented question can be told why, but not by the engine** (finding 3). Presentation
   fields resolve against the state *at presentation time*, so a node on the way back can write the
   reason into a parameter and the question carries it inside its own text. That is composition by the
   author. A plain `resume`, which re-presents without any node in between, still changes nothing and
   still says nothing: ADR 013 §6 is untouched, and the empty `errors` map the finding observed is the
   same map. What was "the engine gives the answerer no way to know" is now "the author has a way and
   the engine still has no rule".

5. **The prediction was measured, and it held.** Every mechanism above was first read in the
   delivered code — `BaseInteractiveAction.process_answer` with the `AskAction` hook under it and the
   engine's call to both, `AskAction.present`, `_visit_cap_reached`,
   `ActionNodeOutput.get_param`/`set_param`, and the ADR 015 tests that exercise the one-node
   accumulating loop. Both halves of the rewrite have since been run: the interpolation half in
   session `2026-08-20-implementation-4`, the fold in `2026-08-20-implementation-5`. Four of the
   flow's eleven nodes — `CHECK_ROOT`, `CHECK_ISSUES`, `FQ_CHECK`, `FQ_COLLECT` — existed only to
   adjust data next to a question, and all four folded into the post function of the question they
   served. **Seven nodes**, as predicted, and the flow covers what it covered before.

   The second effect held too: with the check inside `ASK_ROOT`, a rejected folder re-asks as an
   *attempt* rather than as a fresh visit, so `max_attempts` bounds the loop at the question and the
   node no longer declares `max_visits` at all — nothing in the folded flow leaves a node and comes
   back, which is the only thing the cap is for. The scenario therefore stops exercising ADR 017,
   which is now covered only by `tests/test_adr017_max_visits.py`.

   Two costs the prediction did not name, both paid at the questions that were folded into:

   - **A node that computes cannot also route on the answer text.** The post function's result is the
     whole output, so the surfaced value replaces the text the answerer wrote. `ASK_ROOT` used to read
     the word "abort" out of a success answer; walking away is now the declared failure answer the
     contract always had (`review_abandoned` in the node's catalogue), which is what row `A` maps
     `auto_log_stop` to anyway. `save_as` moves with it: at `ASK_INSPECT` it now keeps the surfaced
     issue list rather than the answer text.
   - **The size of an answered collection is not checkable inside the node that asked.**
     `is_collection_size_at_least` resolves its collection from the state, where an answered value has
     not landed. `CHECK_ISSUES` therefore folded as an equality on the rendered value — an empty issue
     list is literally `[]` (ADR 016) — rather than as the count it used to be. Deliberate: the pair
     was what the decision named, and a guard reading the pending writes of the output is a component
     with its own contract, to be decided when a second flow asks for it.

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
3. ~~Decide text interpolation.~~ Done in session `2026-08-20-architecture-3` and delivered in
   `2026-08-20-implementation-2`: ADR 016 resolves references inside declared template fields, and
   collections render as compact JSON instead of a Python repr. Friction 1 below is closed.
4. **Rewrite the flow against the three decisions.** Half done in session
   `2026-08-20-implementation-4`: ~~the interpolation half~~ is delivered — the three `context: param.x`
   fields of the scenario and the `context` and `hints` of `examples/approve-and-copy.json` now stand
   inside the instruction each question publishes, and the follow-up question shows the ADR 016 JSON
   rendering of a list where the bare field used to show a Python repr. Nothing else changed: no node
   was removed, no engine code was touched, and the flow still runs on the shipped core alone.

   ~~The node-folding half is not done~~ — it is, in session `2026-08-20-implementation-5`, once the
   functions of the next item shipped. The flow is seven nodes; what the fold measured is item 5 of
   "What ADR 015, 016 and 017 changed".
5. ~~**The post function has a mechanism and no component.**~~ Decided into the core in session
   `2026-08-20-architecture-6` and built in `2026-08-20-implementation-5`: `echo_answer` surfaces a
   declared answer value into the output text, `collect_answer` appends the answer to a collection
   parameter and reports `enough` or `more`. Both live in `actions/answer_functions`, and both keep
   the writes the answer carried rather than returning a fresh output. What the decision was, and
   why, is kept below.

   Every fold predicted above needs a function that takes the injected `output` — surfacing an
   answered value, or appending it and reporting "enough" — and no core function takes one: they were shipped with the mechanism only, and the two that prove it live
   in `tests/test_adr015_post_function.py`. `echo_value`, the obvious candidate, cannot serve: it
   reads its value from the state, where the answer has not landed, and returns a fresh output that
   would drop the answered writes. The question the previous re-measurement deliberately left open is
   now answered for the core, on two grounds. The external-first argument assumed an outside that
   would ripen the contract, and there is none: the only consumers live in this repository, and the
   proving-outside role is already played by the test functions, written in the external shape and
   exercised end to end through the CLI. And the yardstick property decides the rest: this scenario
   exists to show what the shipped core alone can carry, and a fold behind an external module would
   not show it. The decision is component work under the delivered ADR 015, not an ADR of its own —
   the precedent is `append_to_param`, added in session `2026-08-19-implementation-15` without one —
   and the names and exact signatures are the implementation session's to choose. What the fold
   costs is unchanged and stays priced by ADR 015 §2.
6. **The script-running function for `S`**, as an external module rather than a core component: it is
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

1. ~~**Interpolation inside text — the one real gap in the core.**~~ **Closed by ADR 016**, delivered
   in session `2026-08-20-implementation-2`. Kept as the record of what was measured and of what the
   decision cost. The gap was: a reference resolved as a whole configuration value, never as a template
   inside a string (ADR 012 deferred §1; ADR 014 open point 1), so "Here is the draft I produced, do you
   approve?" cost an extra node composing the text into a parameter the presentation then referenced.

   The count the decision was waiting for: in the eleven-node flow, **three of the four questions had to
   show a prior value as a field of its own** (`context`) because it could not be written into the
   sentence, and each instruction had to be bent around it — "the folder named below", "the issues
   below". Only the first question, which needs no prior state, escaped. A list shown this way also
   reaches the answerer as a Python repr (`"['a', 'b']"`), so what interpolation has to decide is not
   only where a reference may appear but how a non-string value renders once it is inside a sentence.

   Both halves were decided: the braced `${...}` form resolves in every presentation field of `ask`,
   and a list or a dict renders as compact JSON through the state's own encoder. The flows have since
   been rewritten to use it (session `2026-08-20-implementation-4`): none of the four fields the count
   measured is left, and the measured cost — an extra node composing the text — was never paid.
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
