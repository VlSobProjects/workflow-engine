# Session 2026-08-26-architecture-1

## Type
architecture

## Goal
Hold the data-generation discussion that opens roadmap step 14 and record its decisions: where the
dataset variants of the `load-test-triage` exit scenario come from, how each expected path gets its
data, where the deterministic pre-check ends and the model begins, and the form of the drift-B
experiment protocol.

## Completion criteria
- The data source is decided with alternatives and costs stated: real captures against a live
  system under test versus synthetic generation versus mutation of a captured base.
- The variant map is decided: which capture or derivation produces each expected path of the
  scenario, and which paths need no dataset at all.
- The boundary between the deterministic pre-check and the model's verdict is stated as a
  principle the scenario amendment can carry.
- The composition of the final report is decided: who writes the prose, what stays deterministic,
  and what drift-B measures.
- The drift-B protocol is fixed in form: the reference run, the list of numbers declared before
  the runs, the form of the threshold, and where the protocol and the results live.
- The documents the decisions make stale are amended in this session or the amendment is scoped
  as an explicit next step: the `load-test-triage` scenario, the two-drifts note, roadmap row 14.

## Scope boundaries
- No code: the capture rig, the fault-injection work on the system under test and the
  window-selection scripts are later work; the rig and the system under test live outside this
  repository and appear in documents only by role.
- The concrete emulation recipes per defect are decided later, against the tools and data the
  captures actually produce; this session fixes the map, not the recipes.
- Drift-A (authoring) stays untouched: phase 3 work.

## Status
`completed`

## Result
The discussion was held and every completion criterion closed in this session: the data source,
the variant map, the pre-check boundary, the report composition and the drift-B protocol are
decided and written into the documents they belong to — the protocol as a new section of the
`load-test-triage` scenario body, the answered questions retired from the two-drifts note,
roadmap row 14 rewritten to the remaining work, the hand-build evidence clause extended.

## Decisions
1. **The dataset is captured, not synthesized.** The variants come from real runs of a real
   system under test — an existing web application with a database, run locally — under a real
   load rig, with the injector's metrics exported from the metrics store and the host's resource
   metrics beside them; deployment facts are a small hand-written file per variant. The decisive
   argument: a planted condition lives in several files at once (service log, injector data,
   host metrics), and a real capture keeps that evidence consistent for free, where mutation of
   prepared files would synchronize it by hand. The rig also becomes the stand the publication
   gate needs anyway. Rejected: pure synthetic generators (self-contained and cheap, but the
   texture is fake and the work prepares nothing for the live run); mutation of a captured base
   as the primary mechanism (kept only where it is trivial and consistent — excerpt-window
   selection and hand-edited precondition files).
2. **The variant map.** Seven captures: clean; a flooding thread group (a lost think time floods
   one operation, the injector's own data shows it, the service logs stay clean); a starved
   injector (healthy system, sunk intensity); an injector dying mid-run (its metrics stop, the
   service logs continue); a degrading index (an SQL script against the database); a saturated
   database pool (a limit on the database server); a starved host (fault injection slows every
   operation and loads the memory). Two pre-check variants by hand-editing a precondition file:
   a wrong deployed version, a missing or empty metrics export. The chunked, evidence-loop and
   undecidable paths derive from existing captures by excerpt-window selection; the failure path
   is scripted with the `fake` adapter and needs no data.
3. **The pre-check boundary is a principle.** The pre-check decides only "can this run be
   analyzed at all" — unambiguous precondition facts, one comparison each. Wherever the question
   "why?" is legitimate — and that is most cases — the model judges and the report carries a
   recommendation. The achieved-versus-target comparison stays deterministic but becomes bus
   evidence for the decision instead of an early exit.
4. **The report is model prose over a deterministic appendix.** Every path that ends the
   workflow ends in an `llm` report node that receives declared parameters only — verdict,
   confirmed evidence, route summary — and writes the human deliverable; the ADR 020 functions
   render the appendix the measurement reads. The engine-level failure end stays a failure and
   writes no report.
5. **Checks stay rich; the problems require judgment.** The deterministic checks are not
   weakened to let the model shine; instead the planted problems are chosen so that honest
   checks cannot settle them — the flooding thread group is the exemplar — and the model earns
   its place by the problem.
6. **The gate object is a node-to-model map.** Each `llm` node gets the smallest model that can
   do its step; very small models take narrow judgments with `format: text` and a following
   normalization function node — the bus pattern, no engine change. Calibration runs are
   explicitly separated from measured runs: the map, the answer forms and the prompts are chosen
   freely first, then the numbers are declared, then the measurement runs. Extended measurement
   outside the gate: model substitutions into the map, a single-model map against the mixed one,
   cloud providers.
7. **Where things live.** The drift-B protocol is a section of the scenario body; the concrete
   thresholds are added there by the protocol half of step 14 before the measured runs; results
   land in the measurement sessions' notes — no new document class for one experiment. The
   frozen captures' storage is decided after the first capture shows their compressed size: the
   repository if it permits, a release asset if not. The rig and the system under test live
   outside this repository and appear in documents by role only.
8. **The hand-build purity process.** The internal documentation is written first, the
   operator-facing draft is derived from it, and the operator then authors the definition from
   that documentation alone — recording every mistake and whether the error text led to the fix,
   as G11 evidence. A divergence between the built workflow and the expectation is triaged into
   "change the instructions" or "change the code". The phase 2 claim is documentation
   sufficiency, not author blindness; blindness is phase 3.

## Open questions
- The concrete emulation recipes per defect: decided against the actual tools when the rig
  exists.
- The storage of the frozen captures: decided after the first capture.
- Whether the `llm` node needs the ADR 015 post-function seat, or the normalization function
  node suffices: decided by the pain of the build, under an ADR if it comes.
- The numeric thresholds of the protocol: the protocol half of step 14, declared before the
  measured runs.

## Next steps
1. Outside this repository: the fault-injection surface on the system under test, the load rig,
   the first captures.
2. The remaining step 14 work in this repository: the domain parsing module with the
   window-selection scripts, then the declared thresholds into the scenario's protocol section.
3. Step 15: the operator-facing documentation draft, then the hand-build and the measured runs.

## References
- Branch: `docs/data-generation-discussion`
- ADRs: ADR 014, ADR 020, ADR 021 (all frozen; read, not changed)
- Documents changed: `docs/architecture/scenarios/load-test-triage.md`,
  `docs/architecture/notes/2026-08-25-two-drifts-and-their-measurement.md`,
  `docs/architecture/roadmap.md`, this note
