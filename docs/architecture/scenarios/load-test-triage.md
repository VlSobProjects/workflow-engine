# The load-test triage that explains its verdict

- **Identifier:** `load-test-triage`
- **Class:** `2`
- **Answerers:** nobody answers from outside — this is the first fully automatic scenario, the
  second archetype of ADR 014. Deterministic steps are registered functions; the aggregate and
  decide steps are `llm` nodes the engine calls itself through a registered provider adapter — a
  local model behind an OpenAI-compatible server, a small model for aggregation and a larger one
  for the decision, chosen per node. In tests the `fake` adapter answers with scripted replies.
  The human appears once, at the end, as the recipient of the handover — never as an answerer.
- **Input data:** one completed load-test run of a fictional order-processing service, prepared on
  disk as four files: the load profile the test was meant to apply (operations, target rates, ramp
  — JSON), the test report aggregated per operation (throughput, latency percentiles, error rates
  — CSV), an excerpt of the service logs covering the run window (plain lines), and the deployment
  facts (service versions, instance counts, queue and index configuration — JSON). The formats are
  neutral on purpose: no load-testing tool is named, and the publication gate replaces the
  prepared files with a live system under test. One prepared variant of the dataset per expected
  path: each variant plants the evidence that selects its path.
- **Expected paths:** the pre-check path, where a deterministic comparison answers before any
  model is called; the clean path; the test-defect and system-defect verdicts, the latter
  branching per subsystem; the chunked aggregation loop under `context_overflow`; the evidence
  loop when the decision wants deeper data, bounded by `max_visits`; the handover when the
  evidence decides nothing; failure when a reply or the provider fails past the retry bound. Each
  path is selected by its dataset variant. Details in the body.
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
by phase 3 in its assisted form; the hand-build of this scenario (roadmap steps 10 and 12), made
deliberately from the operator documentation alone, gives gap G11 the lower bound of the authoring
need.

## What ships where

The core gains only generic bus work: creating and setting a dictionary parameter, splitting a
text into bounded chunks, accumulating findings — forms any workflow can reuse. Reading and
parsing the domain files — the profile, the report, the log lines, the deployment facts — ships
as an external module (ADR 005) beside the scenario, the way a consumer's formats stay outside
the core. Together with the provider adapter for the local server, itself the first real external
module (ADR 014 §2), the scenario exercises the plugin path with real consumers, which nothing
has done yet.

## The flow shape

- **Fetch.** Start parameters (ADR 012) point the run at the dataset. Registered functions of the
  domain module read each file into typed parameters on the bus; the checks at the boundary are
  code — the files exist, the collections are non-empty — through the existing validators.
- **Pre-check.** A pipeline of checks answers before a model is called. A deterministic
  comparison of the profile against the report — achieved rate versus target rate per operation —
  declares miscalibrated load without any model, and a run whose load never happened ends here.
- **Aggregate.** A small model turns the log excerpt into structured findings: errors grouped by
  subsystem, saturation signals, timing anomalies. The engine enforces the limit of the step: the
  prompt interpolates only the declared parameters (ADR 016), and the model sees nothing else.
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
  the report states it. The queues verdict is confirmed against the queue configuration and the
  error findings, the scaling verdict against instance counts and the throughput curve, the
  indexing verdict against the operations whose latency degrades with volume. A claim the code
  cannot confirm routes to the handover, not into the report.
- **Hand over.** The report — the verdict, the confirmed evidence, the route as the journal
  recorded it — is composed into a document and exported as the deliverable (ADR 011). The
  unforeseen exit is the same node reached by failure transitions: the report then states why the
  flow stopped and hands over the evidence collected so far. The engine never invents a step.

## The journal explains the path

The done condition requires the path to be explained by the journal, not by the model's memory.
Every call journals `llm_called` with provider, model and status; prompts and replies are recorded
as artifacts under `record: true` (ADR 014 §4); the guard traces say why each transition fired;
and the read surfaces of ADR 018 let the analyst walk the route after the fact. A second run on
the same prepared variant takes the same path, and the journal shows it.

## Expected paths

1. **Pre-check verdict.** The achieved load never reached the profile's target; the deterministic
   comparison declares miscalibrated load; no model is called; the report exports.
2. **Clean.** Aggregation finds no anomaly, the decision answers clean, the report says so.
3. **Test defect.** The findings show the injector's own failures — connection errors on the
   generator side, a scenario shape the service never sees in production; the decision names the
   test, the confirmation holds, the report blames the test, not the system.
4. **System defect.** The planted evidence names a subsystem — queue saturation, an index
   degrading with volume, instances that never scaled; the decision names it, the per-subsystem
   branch confirms it in code, the report carries the confirmed claim. One dataset variant per
   subsystem.
5. **Chunked aggregation.** The oversized log variant: the first aggregation call refuses with
   `context_overflow`, the chunk loop splits, visits and accumulates, and the run continues as
   paths 2–4.
6. **Evidence loop.** The decision answers `need_more_evidence`; a deeper fetch narrows the
   window; the re-entry counts against `max_visits`, and exhaustion routes to the handover with
   what was collected.
7. **Handover.** The undecidable variant: the evidence is contradictory or missing; the decision
   declares it, or a confirmation refuses the claim, and the run ends with the handover report
   stating why it stopped.
8. **Failure.** A reply that never parses (`llm_answer_invalid`) or a `permanent` provider
   refusal past `max_attempts` fails the run under its code.

## Open decisions the scenario lacks

1. **No `llm` node.** The central step of every path but the first does not exist; ADR 014
   (Draft) decides it — the action, the provider registry, the `fake` adapter, the `providers`
   configuration, the error classes, the call audit — and this scenario is the consumer it names.
2. **Nothing assembles the aggregate into a dictionary.** The chunk loop has its splitter
   (`split_text_to_deque`) and its accumulators (`append_to_param`, `collect_answer`) since the
   ADR 014 variants; what remains of gap G5 is the dictionary half — no function creates or sets a
   dictionary parameter. Built as component work under ADR 006 when this scenario names its
   aggregate step — this document is that naming.
3. **The verdict's keys are unchecked.** The decision binds a dict and `type: dict` accepts any
   dictionary (gap G4); the guard over answer keys is component work under ADR 002, and this
   scenario is the trigger that decision named.
4. **The handover has no document shape.** The report is a composed document; the core renders a
   table, cannot write composed text into a file or an artifact, and an artifact name cannot
   carry a run value (gap G6). The output family is ADR 020 (opened at roadmap step 7 from
   the `result-file-composition` note), ahead of ADR 014; the hand-build measures whether the
   delivered family carries this handover.
5. **Every failure route is written per node.** The handover on the unforeseen exists only as
   explicit failure transitions on every node (gap G7); the verbosity of the hand-written flow is
   the trigger for a workflow-level default failure route.
6. **The authoring half is unmeasured.** The authoring claim has no authoring surface — no
   validation without a run, no description of a definition (gap G11); the hand-build gives the
   lower bound, and `workflow-authoring` mechanizes the same claim as a workflow in phase 3.
7. **Where the prompts live.** The aggregation and decision prompts are paragraphs of instruction,
   not lines; whether inline template text suffices or the authored-file channel (`prompt_ref`,
   deferred by the narrowed ADR 014 until a scenario asks) must return is measured by the
   hand-build.
