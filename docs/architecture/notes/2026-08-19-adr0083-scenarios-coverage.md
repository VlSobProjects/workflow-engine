# Can this engine carry the ADR-0083 questionnaire scenarios?

- **Date:** 2026-08-19
- **Trigger:** question raised while preparing ADR 013 for implementation (session
  `2026-08-19-architecture-2`): ADR-0083 of the external `java-claude-ai` repository — a
  JSON-configured questionnaire engine with a six-type node graph — is where this project started
  before it went its own way. Can its *scenarios* (not its contract) be realized here once ADR 013
  ships, given some external registered functions?
- **Status:** open
- **Affected:** ADR 010 (budget checkpoint shape), ADR 012 (deferred §1, shallow reference
  resolution), ADR 013 (Implementing), ADR 014 (Draft, decides prompt templating)

The answer is yes for the substance, with one core gap, one shape difference, and one function to
write. Recorded here because the mapping keeps being re-derived, and because two of the three
frictions belong to decisions that are still open.

## What ADR-0083 asks for, and what carries it here

| ADR-0083 | Carried by | Verdict |
| --- | --- | --- |
| `Q` — one prepared question to the operator | `ask` node: text and options in the presentation, a typed `answer` entry; `input_mode` is expressed by the codec (`path` → `pathlib.Path`) | full |
| `A` — agent branch decision, no dialogue | the same `ask` node, answered by an agent; `allowed_values` is an `any_of` of `equals` guards; `default` with `require_reason` is a `failure` answer with a code and a message; `auto_log_stop` is a `FailTarget` plus the `interactive_answered` event | full |
| `I` — instruction to the agent to act and report | the same `ask` node: the presentation is the instruction, the agent acts outside the engine and answers with the aggregated result; node `validators` already exist | full |
| `S` — deterministic script with parameters | a `function` node over an external registered function that runs the script; `script_output_match` is several transitions with `contains` guards, whose configured value resolves `param.` references | needs one external function |
| `STOP` | `stop` / `stop_on_error` and the `EndTarget` / `FailTarget` transition targets; `handoff_ref` is a deliverable (ADR 011); `cleanup_scripts` is a node before the end | full |
| `FQ` — up to N agent-generated questions | a self-loop of `ask` bounded by `max_attempts`, accumulating into a list parameter through the existing collection-writing functions; or one node whose declared answer is a list of question/answer pairs | expressible, more verbose |
| typed validators (`non_empty`, `regex`, `enum`, `path_exists`) | node `validators`, value guards, function guards | full |
| `attempt_counters`, `max_visits`, retry actions | `attempt_counters` / `max_attempts`, `visit_counters` — the same mechanism, which came from there | full |
| logging: engine-authored vs agent-authored fields per node | `session_events` (the engine/operator actor split), `guard_results`, `outputs`, `errors`; the agent's verbal part is the answer's `text` and `message` | in substance, but the verbal part lives in the state, not in the journal: the journal deliberately never stores values |
| `recommended_answer` | presentation fields (`options`, `examples`, `hints`, `context`) | full |
| persistence `set` / `append`, artifacts vs structured facts | `WriteParamMode.SET` / `APPEND`, `state.params` for facts, artifacts and deliverables for documents (ADR 011) | the result is the same; the stance is the opposite — see below |

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
