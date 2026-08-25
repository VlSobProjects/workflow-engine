# The load-test triage that explains its verdict

- **Identifier:** `load-test-triage`
- **Class:** `2`
- **Answerers:** nobody answers from outside — this is the first fully automatic scenario, the
  second archetype of ADR 014. Deterministic steps are registered functions; the aggregate and
  decide steps are `llm` nodes the engine calls itself through a registered provider adapter — a
  local model behind an OpenAI-compatible server, a small model for aggregation and a larger one
  for the decision, chosen per node. In tests the `fake` adapter answers with scripted replies.
  The human appears once, at the end, as the recipient of the handover — never as an answerer.
- **Input data:** one completed load-test run of a real system under test — a web application
  with a database, run locally under a real load rig — captured on disk as files: the load
  profile the test was meant to apply (operations, target rates, ramp — JSON, authored per
  variant), the injector's report and metrics as the load tool exports them, the resource metrics
  of the host as the metrics store exports them, an excerpt of the service logs covering the run
  window, and the deployment facts (service version, instance count, database and pool
  configuration — JSON, hand-written per variant). The formats are the real export formats of the
  rig's tools, parsed by the domain module that ships beside the scenario; the publication gate
  reuses the same rig against the live system instead of the frozen files. Most variants are
  separate captures whose planted condition is induced for real — fault injection in the system
  under test, limits on the database server, a misconfigured or starved injector — because a real
  capture keeps the evidence consistent across all files at once; the remaining variants derive
  from a capture by selecting the log window or by hand-editing a precondition file. The rig and
  the system under test live outside this repository and appear here by role only.
- **Expected paths:** the pre-check exit, where a failed precondition makes the run not worth
  analyzing; the clean path; the test-defect verdicts, where the load was applied wrong or the
  injector itself failed; the system-defect verdicts, branching per subsystem the system under
  test really has; the chunked aggregation loop under `context_overflow`; the evidence loop when
  the decision wants deeper data, bounded by `max_visits`; the handover when the evidence decides
  nothing; failure when a reply or the provider fails past the retry bound. Each path is selected
  by its dataset variant. Details in the body.
- **Ends with:** end of workflow with the triage report exported as the deliverable — the verdict,
  the confirmed evidence and the route the run took; the handover is also an end of workflow, its
  report stating why the flow stopped and carrying the evidence collected so far, with the
  exhausted evidence loop routed there like any other error code; failure under
  `llm_answer_invalid` or a provider error class when `max_attempts` exhausts.
- **ADRs exercised:** ADR 005, ADR 006, ADR 011, ADR 012, ADR 014, ADR 016, ADR 017, ADR 018, ADR 020, ADR 021

## The consumer

This is the exit scenario of phase 2: the done condition of `docs/architecture/purpose.md`
describes this run, and the roadmap closes the phase when it passes. The recipient of the run is
the load-testing analyst, who gets a verdict they can trust or a handover they can act on — never
a silent stop. ADR 014 names this scenario in its `Consumer` section as its phase consumer: every
judgment step here is an `llm` node; the evidence at that ADR's own freeze gate is the class 4
inventory variants it names beside it, because this scenario gates the phase — and with it every
ADR of the phase (`2026-08-24-architecture-1`). The authoring half of the done condition is gated
by phase 3 in its assisted form; the hand-build of this scenario (roadmap step 15), made
deliberately from the operator documentation alone, gives gap G11 the lower bound of the authoring
need.

## What ships where

The core gains only generic bus work: creating and setting a dictionary parameter, splitting a
text into bounded chunks, accumulating findings — forms any workflow can reuse. Reading and
parsing the domain files — the profile, the injector export, the host metrics, the log lines,
the deployment facts — ships as an external module (ADR 005) beside the scenario, the way a
consumer's formats stay outside the core. The scripts that derive a variant from a frozen
capture — the excerpt-window selection — live beside that module; the capture rig and the system
under test live outside the repository. Together with the provider adapter for the local server,
itself the first real external module (ADR 014 §2), the scenario exercises the plugin path with
real consumers, which nothing has done yet.

## The flow shape

- **Fetch.** Start parameters (ADR 012) point the run at the dataset. Registered functions of the
  domain module read each file into typed parameters on the bus; the checks at the boundary are
  code — the files exist, the collections are non-empty — through the existing validators.
- **Pre-check.** A pipeline of checks answers one question before any model is called: can this
  run be analyzed at all. The boundary is a principle: the pre-check decides only what one
  unambiguous comparison decides — the deployed version is not the expected one, the metrics
  export is missing or empty — and exits early with the reason. Wherever the question "why?" is
  legitimate, the run passes the pre-check and the model judges. The deterministic comparison of
  achieved rate against target rate stays, but its result is evidence on the bus for the
  decision, not an early exit.
- **Aggregate.** A small model turns the log excerpt into structured findings: errors grouped by
  subsystem, saturation signals, timing anomalies. The engine enforces the limit of the step: the
  prompt interpolates only the declared parameters (ADR 016), and the model sees nothing else.
  Each step runs on the smallest model that can do it: a narrow judgment — one finding, one short
  answer — may use a very small model with `format: text`, followed by a function node that
  normalizes the reply and extracts what the guards check; the structure lives in the functions,
  not in the small model's answer.
  When the excerpt exceeds the model's context, the provider refuses with `context_overflow`
  (ADR 014 §5) and a guard routes into the chunk loop: a splitter function fills a deque, the
  `llm` node visits once per chunk, an accumulating function collects the findings — the graph
  pattern of ADR 014 alternative F, never the action's hidden behaviour.
- **Decide.** A larger local model reads the accumulated evidence — the findings, the report
  aggregates, the deployment facts — and answers with a typed verdict: the verdict word from a
  closed list, the suspected subsystem, the rationale. `equals`/`any_of` guards on the verdict
  word select the branch; the model is never a guard. The decision may also answer
  `need_more_evidence`, routing back through a deeper fetch — a narrower log window around the
  first anomaly — and into the decision again; the loop is bounded by `max_visits` (ADR 017).
- **Branch.** Per-verdict deterministic confirmation: code verifies what the model claims before
  the report states it. The subsystems are the ones the system under test really has: the
  database-pool verdict is confirmed against the configured pool limit and the timeout errors in
  the log, the index verdict against the operations whose latency degrades with volume, the
  resource verdict against the host metrics, the test-defect verdict against the profile and the
  injector's own data. A claim the code cannot confirm routes to the handover, not into the
  report.
- **Hand over.** Every path that ends the workflow ends in a report an `llm` node writes as
  prose — the verdict explained, the confirmed evidence, a recommendation where the verdict
  implies one — over a deterministic appendix the output family renders (ADR 020): the route as
  the record channel kept it, the check results, the tables; the document exports as the
  deliverable (ADR 011). The report node receives declared parameters — the verdict, the
  confirmed evidence, the route summary — never the raw files. The prose is the deliverable for
  the human; the appendix is what the measurement reads. The unforeseen exit is the same node
  reached by failure transitions: the report then states why the flow stopped and hands over the
  evidence collected so far. The engine never invents a step.

## The journal explains the path

The done condition requires the path to be explained by the journal, not by the model's memory.
Every call journals `llm_called` with provider, model and status; prompts and replies are recorded
as artifacts under `record: true` (ADR 014 §4); the guard traces say why each transition fired;
and the read surfaces of ADR 018 let the analyst walk the route after the fact. A second run on
the same prepared variant takes the same path, and the journal shows it.

## Expected paths

1. **Pre-check exit.** A precondition fails — the deployed version is not the expected one, or
   the metrics export is missing or empty; nothing is worth analyzing, no judging model is
   called, and the report states why the run was not analyzed. Produced by hand-editing a
   precondition file of any capture; one variant per precondition.
2. **Clean.** A normal capture: aggregation finds no anomaly, the decision answers clean, the
   report says so.
3. **Test defect: the load was applied wrong.** A thread group with a lost think time floods one
   operation at the maximal rate and the other virtual users starve. The injector's own data
   shows the flood, the service logs carry no error of the system's own; the decision blames the
   test, the confirmation checks the claim against the profile and the injector data, and the
   report recommends fixing the script. Induced for real in the load rig.
4. **Test defect: the injector failed.** Two captures: an injector short of capacity — the
   system is healthy but the achieved intensity sinks below the target; and an injector that
   dies mid-run — its own metrics stop at a moment the service logs pass in silence. The
   decision blames the test infrastructure, and the report recommends the remedy — more injector
   capacity, a bigger injector heap or a leaner script. Induced for real: a starved injector, a
   capped injector heap.
5. **System defect.** One capture per subsystem the system under test really has: an index
   degrading with volume (an SQL script against the database), a saturated database pool (a
   limit on the database server), a starved host (fault injection: every operation slowed and
   the memory loaded — the decision must connect the metrics to the latency). The decision names
   the subsystem, the per-subsystem branch confirms it in code, the report carries the confirmed
   claim.
6. **Chunked aggregation.** No capture of its own: the full log of any capture exceeds the
   model's context, the first aggregation call refuses with `context_overflow`, the chunk loop
   splits, visits and accumulates, and the run continues as paths 2–5.
7. **Evidence loop.** No capture of its own: the first excerpt window is chosen to graze the
   planted evidence, the decision answers `need_more_evidence`, and a deeper fetch narrows the
   window over the same frozen capture; the re-entry counts against `max_visits`, and exhaustion
   routes to the handover with what was collected.
8. **Handover.** No capture of its own: the excerpt window is chosen against the metrics — the
   metrics show an anomaly while the log window covers a quiet stretch; the evidence is
   contradictory, the decision declares it or a confirmation refuses the claim, and the run ends
   with the handover report stating why it stopped.
9. **Failure.** A reply that never parses (`llm_answer_invalid`) or a `permanent` provider
   refusal past `max_attempts` fails the run under its code; scripted with the `fake` adapter,
   no dataset needed.

## The drift-B measurement

The run of this scenario is the drift-B experiment of the two-drifts note
(`2026-08-25-two-drifts-and-their-measurement`): one definition, several models, the distance
measured from a known point. The protocol:

- **The reference run is the `fake` adapter.** Scripted replies per variant give a deterministic
  route and a deterministic verdict; a model run is then a distance from that point, not an
  impression.
- **The gate object is the declared node-to-model map, not one model.** The definition assigns
  each `llm` node the smallest model that can do its step — a very small model on the narrow
  judgments, a mid-size one on aggregation, the largest local one on the decision. The phase
  gate is this one map matching the declared numbers on the gate variants with local models.
- **Calibration is separated from measurement.** Calibration runs — choosing the map, the answer
  forms, the prompts — happen first and freely; then the numbers are declared; then the measured
  runs either match them or do not. A number declared after the runs is worthless.
- **The declared numbers, per variant and map:** whether the route matched the reference (the
  node sequence read from the ADR 021 record channel, never reconstructed); whether the verdict
  word matched the planted truth; whether the planted cause is named in the confirmed evidence;
  the counts of `llm_answer_invalid` and retries; whether the run reached a terminal path or
  died under `max_attempts`. The prose of the report is the deliverable, not a metric.
- **Extended measurement, outside the gate:** other local models substituted into the map, a
  single-model map against the mixed one — the measured form of the claim that decomposition
  makes small models useful — and cloud providers. A model that fails is a data point about the
  required capability, not a gate failure.
- **Where things live:** the protocol is this section; the concrete thresholds are added here by
  the protocol half of roadmap step 14, before the measured runs; the results land in the notes
  of the measurement sessions.

## Open decisions the scenario still lacks

The list this section opened with is mostly closed: the `llm` node, the provider seat, the `fake`
adapter, the error classes and the call audit are ADR 014 and ADR 021, accepted; the dictionary
half of gap G5 (`init_dict_param`, `set_dict_item`, `append_to_dict_key`) and the answer-keys
guard of gap G4 (`is_answer_keys_valid`) shipped at roadmap step 10; the output family of gap G6
is ADR 020, delivered. What remains open:

1. **Whether the delivered output family carries the appendix.** The prose half of the report is
   decided — an `llm` node writes it on every end-of-workflow path; what the hand-build (roadmap
   step 15) still measures is whether the deterministic appendix — route, check results, tables —
   composes from the ADR 020 functions without a new shape.
2. **Every failure route is written per node.** The step 10 reading — a third of the
   `reorganize-folder` definition is failure plumbing (gap G7) — supports the suspicion; the
   trigger for a workflow-level default failure route stays this scenario's hand-build, as
   decided.
3. **Where the prompts live.** The step 10 reading: inline template text carries a
   paragraph-length prompt mechanically and hurts editorially; the triage prompts decide whether
   the authored-file channel (`prompt_ref`, deferred by the narrowed ADR 014 until a scenario
   asks) must return.
4. **The authoring half is unmeasured.** The authoring claim has no authoring surface — no
   validation without a run, no description of a definition (gap G11); the hand-build gives the
   lower bound, and `workflow-authoring` mechanizes the same claim as a workflow in phase 3. The
   hand-build also records, for every deliberate or accidental mistake, whether the error text
   led the author to the fix — the error surfaces are part of the documentation the claim rests
   on.
5. **The data is decided but not captured.** The source, the variant map and the protocol were
   decided by the data-generation discussion (`2026-08-26-architecture-1`); what remains of
   roadmap step 14 is the rig and fault-injection work outside the repository, the captures, the
   domain parsing module with the window-selection scripts, and the declared thresholds. Where
   the frozen captures are stored is decided after the first capture shows their compressed
   size: in the repository if it permits, as a release asset if not.
