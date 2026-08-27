# Session 2026-08-28-architecture-1

## Type
architecture

## Goal
Assess how far the delivered clean line of the system under test satisfies the `load-test-triage`
scenario, answer the two open questions the SUT project addressed to this project, and fix the
injector data source the domain parsing module will be written against.

## Completion criteria
- The readiness assessment is recorded: which scenario needs the SUT clean line covers, which
  remain, and which project owns each remainder.
- The two open questions on the SUT project's exchange desk — orchestrator symptoms, recovery
  after overload — are answered there, and the answers with their rationale are recorded here.
- The injector data source is decided with alternatives and costs stated.
- The rendered-panels idea raised by the SUT infrastructure is captured as an architecture note.
- The next steps are ordered across the three projects: this one, the system under test, the
  load rig.

## Scope boundaries
- No code: the domain parsing module, the window-selection scripts and the thresholds stay the
  remaining work of roadmap step 14.
- No scenario amendment: the variant map, the pre-check boundary and the drift-B protocol decided
  by `2026-08-26-architecture-1` stand unchanged; this session measures the world against them.
- The load-rig project itself and the SUT's fault-surface phase are other projects' work; they
  appear here as next steps only.
- No ADR is opened; the image-channel idea is captured as a note, not decided.

## Status
`completed`

## Result
Every completion criterion closed. The SUT clean line was read against the scenario's five input
files and the variant map and found sufficient on its side; the gaps are the absent load rig, the
SUT's own fault-surface phase, one unowned variant and the fact that no load run has happened yet.
Both exchange questions were answered `no` on the SUT project's exchange desk. The injector data
source is fixed. The rendered-panels idea is a note. The cross-project step order is recorded
under next steps.

## Decisions
1. **The SUT clean line satisfies the scenario's SUT-side needs.** Of the scenario's five input
   files, three are served today — the metrics-store export over its API, the service log with
   the verified pool-timeout signature, the deployment facts readable from three agreeing
   places — and the remaining two (the load profile, the injector's report and metrics) belong
   to the load rig. Nothing in the clean line needs rework for the scenario. What remains is
   elsewhere: three of the seven capture variants are rig-side work; the degrading-index variant
   waits on the SUT's own fault-surface chain (the indexed report, seeding at volume, the fault
   script); the saturated-pool variant has its mechanism but not its under-load evidence; and no
   variant is producible until the rig exists, because no load run of any kind has been made —
   the service levels are chosen, not measured, and the calibration rule has never been checked
   under load.
2. **Orchestrator symptoms: no.** Answered on the exchange desk. The captures stay
   container-level and host-level; the platform underneath is not a subject of the verdict. The
   variant map has no orchestrator variant, the system-defect verdicts branch per subsystem the
   system under test really has, and the phase gate needs none of it. The SUT's Compose decision
   stands. A cloud cluster deployment of the stack is kept as a late-stage idea — publication or
   beyond — and if it ever happens, the question reopens together with that stand, never before.
3. **Recovery after overload: no for phase 2.** Answered on the exchange desk. The variant map is
   frozen and carries no persistent-degradation shape; adding one would reopen a decided map and
   put an unowned third fault surface into a phase whose gate does not need it. The shape is
   acknowledged as the most production-like verdict a triage could learn and stays a candidate
   for extended measurement or a later phase; the stepped maximum-finding run may still happen as
   rig-side calibration, but this project imposes it as no prerequisite.
4. **The injector data source is the load tool's own result log (JMeter JTL/CSV).** The domain
   parsing module reads one format: per-sample timestamped records, from which achieved intensity
   over time, the flood of one operation and the moment an injector's own data stops are all
   computable — the three injector-side variants need nothing more. Rejected as the capture
   source: a time-series database fed by the tool's backend listener (InfluxDB) — a further
   container on the shared capture host, writes to the disk whose read pressure is evidence, and
   a second export format for the same facts. That idea is deferred, tied to the possible
   late-stage cloud deployment of decision 2, where a live view has a host of its own to run on.
5. **Rendered panels as model input is a note, not phase 2 work.** The SUT infrastructure ships a
   renderer that turns any dashboard panel into an image file. Feeding such images to
   image-capable models conflicts with nothing — but the `llm` action of ADR 014 has a text-only
   prompt channel, so an image input is a future ADR, and the SUT stack's own principle holds
   that a render is a convenience of the analysis side and never a source of evidence. Its place
   is extended measurement outside the gate, or later; captured as the
   `2026-08-28-rendered-panels-as-model-input` note.
6. **The starved-host variant needs an owner.** It is the one variant of the map excluded from
   the SUT brief's scope, absent from the rig specifications and owned by nobody. Proposed home:
   the load-rig project, which already owns the host-level seat beside the injector; to be
   confirmed when that project is started.

## Open questions
- The concrete JTL parsing shape (which columns, which listener configuration) is decided when
  the first real script produces one; the module's injector half waits for that file.
- The account count and the discussion-scenario convergence mechanism are the rig's answers to
  the SUT project's specification; the SUT seeding item waits on them.
- Where the frozen captures are stored: unchanged from `2026-08-26-architecture-1`, decided after
  the first capture.

## Next steps
1. Load-rig project: create it, hand it the two SUT specifications and the starved-host proposal,
   fix the JTL listener configuration, write the day-profile script skeleton, smoke-run it at
   small scale, and answer the SUT specification's questions (accounts, mix survival,
   convergence).
2. SUT project: the fault-surface phase in its recorded order — the indexed report operation,
   then seeding at volume with the rig's account count, then the two fault scripts and the
   acceptance dry run.
3. Calibration campaign across the projects: resources, intensities, skew and service levels
   chosen freely, as the drift-B protocol requires, before any number is declared.
4. This project, in parallel after step 1: the domain parsing module for the already-stable
   formats (metrics-store export, service log, deployment facts), the injector half once the
   first real JTL exists, then the window-selection scripts and the declared thresholds.
5. On the merge of this branch: the session registry row and the note registry row.

## References
- Branch: `docs/sut-exchange-answers`
- ADRs: ADR 014, ADR 020, ADR 021 (read, not changed)
- Documents created: `docs/architecture/notes/2026-08-28-rendered-panels-as-model-input.md`,
  this note
- Outside this repository: the two answers written on the SUT project's exchange desk
  (orchestrator symptoms, recovery after overload)
