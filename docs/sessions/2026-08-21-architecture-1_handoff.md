# Session note

## Type
architecture

## Goal
Work ADR 014 (LLM node and provider adapter) from Draft: re-baseline the draft against the ADRs
accepted since it was written (015, 016, 017, 018), settle its six open points in critical mode,
and decide the transition — POC or Implementing.

## Completion criteria
1. Each of the six open points at the end of the ADR 014 Decision section is answered or explicitly
   deferred, with alternatives and costs stated.
2. The ADR 014 text reflects the settled decision (edited in place on `development`, as the process
   allows for a Draft) and its change log records the session.
3. The transition out of Draft is decided and, if taken, reflected in the registry row; if a POC is
   chosen, its question is stated in the ADR.
4. Open notes intersecting ADR 014 have their `Affected`/`Status` reconciled where the discussion
   touches them.
5. This session note is completed and committed.

## Scope boundaries
- No implementation and no POC code in this session: code work starts only in the branch the decided
  transition creates.
- Retry/backoff policy stays out: recovery note (b) remains the next ADR after 014 and only its
  error-class interface is decided here.
- Token/cost budgets (ADR 010 neighbourhood) stay out of scope, as the draft already states.
- The uncommitted sharpening of `2026-08-18-adr012-deferred-questions.md` predates this session and
  is handled as its own commit, not folded into this session's changes.

## Status
completed

## Result
All six open points of ADR 014 are settled and recorded in its text and change log; the ADR stays
Draft on `development`, ready to enter Implementing — the transition decision is "Implementing, no
POC", executed when the implementation session opens its branch. The registry row gained ADR 016 in
`Depends on`; the recovery note's `Affected` gained ADR 014. No code changed.

## Decisions
All belong to ADR 014 (Draft); numbered by the draft's original open points.
1. **(point 6)** The dedicated `llm` action stays as the automatic counterpart of `ask` across the
   trust boundary: `ask` binds an answer from outside the engine, `llm` is a call the engine owns
   and audits. The fold into a driver over `ask` is rejected alternative E (per-call pause/resume
   round trips, orchestration and audit in an unversioned driver, error classes impossible).
2. **(point 1)** The prompt inherits the ADR 016 template-text contract whole; `prompt_ref` narrows
   to an authored file, defined as a channel of the template-text field kind (one loader, `prompt`
   its only instance; the `ask` fields join by a later decision). Artifact-sourced prompts and the
   instruction-formatting module (prompt template libraries, per-model formatting) are deferred to
   Leaves open; a registered function assembling into a parameter is the sanctioned channel now.
3. **(point 2)** The OpenAI-compatible adapter is the first external module, kept in this
   repository as the reference plugin; the core ships only the `fake` null adapter, which also
   settles the §6 placement question.
4. **(point 3)** `@register_provider` is a real fifth registry, following the one-kind-one-registry
   pattern; the adapter signature is fixed text-in/text-out, structured messages and history
   deferred until a scenario shows them.
5. **(point 4)** The provider block is not snapshotted into `session.json`: it is environment, not
   run identity, providers have no bootstrap problem, and the per-call journal carries
   reproducibility.
6. **(point 5)** The codec decoding of the reply is one code path with the ADR 013 answer binding;
   reply parsing (`format`) and failure semantics stay the action's own.

## Open questions
None new. Deferred items live in the ADR's Leaves open: artifact-sourced `prompt_ref`, the
instruction-formatting module, the `ask` template-file channel, structured messages and history,
retry/backoff (recovery note (b)), token/cost budgets.

## Next steps
1. Move ADR 014 to Implementing when implementation starts: create
   `feature/adr_014-llm-node-and-provider-adapter`, set status and active branch on `development`,
   and build against the acceptance scenario in the ADR's implementation notes.
2. Recovery note (b) — retry/backoff by error class — stays the next ADR after 014, consuming the
   error classes fixed here.
3. Friction 3, the script-running function for `S`, as an external module (unchanged).

## References
- Branch: `development` (Draft ADR per `docs/adr/process.md` git linkage)
- Subject: `docs/adr/adr-014-llm-node-and-provider-adapter.md`
- Changed: `docs/adr/adr-014-llm-node-and-provider-adapter.md`, `docs/adr/README.md`,
  `docs/architecture/notes/2026-08-18-recovery-and-resilience-roadmap.md`,
  `docs/architecture/notes/README.md`, this note
- Previous session: `2026-08-21-implementation-1_handoff.md`
