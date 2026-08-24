# Session note: 2026-08-24 architecture 1

## Type
`architecture`

## Goal
Execute roadmap step 6 — ADR 014 to the narrow Draft, ADR 019 decoupled with the three
shared-mechanism guards, both `Consumer` sections filled — and settle with the owner where the
freeze evidence of ADR 014 comes from and what precedes its implementation.

## Completion criteria
- ADR 014 carries the narrow decision — the action with `format` parsing, the provider registry
  with the `fake` adapter, the `providers` configuration, the call audit and the error classes —
  with the cut items in Leaves open with their triggers.
- ADR 019 no longer constrains ADR 014, and both Drafts record the three shared mechanisms: the
  answer-shape generator, the single template-file loader, and `node.` as a prefix of the
  template-text contract.
- Both `Consumer` sections are filled; `repository-interview` lists ADR 019 in the same session.
- The freeze-gate consumer of ADR 014 and the order of the next steps are decided, written into
  the roadmap, and recorded in the ADRs — and, where not yet ripe for an ADR, as an architecture
  note.

## Scope boundaries
- No code, no tests, no examples.
- The G9 narrowing of ADR 019 beyond the decoupling stays with its roadmap step.
- The output-family ADR itself is not opened here; this session captures its input note and its
  place in the order.
- The notes status edits of the 2026-08-23 triage stay with the maintenance step.

## Status
`completed`

## Result
- ADR 014 is the narrow Draft: `pre_functions`/`post_functions` and `prompt_ref` in Leaves open
  with triggers, §7 recording the shared mechanisms, alternative G added, the adapter package
  homed in this repository with its protocol left to the module. `Consumer` names the class 4
  `described`/`tiered`/`chunked` variants of `folder-inventory-to-csv` as the freeze evidence and
  `load-test-triage` as the phase consumer. Not moved to Implementing — deferred behind the
  output-family ADR (Decisions 2).
- ADR 019 is decoupled, with the three mechanisms recorded on its side (§5, §6, §7) and
  `Consumer` naming `repository-interview`; the scenario and its registry row list ADR 019.
- The note `2026-08-24-result-file-composition` captures the operator's report on the unreadable
  flat output; roadmap steps 6–13 are rewritten: the output-family ADR is step 7, the ADR 014
  implementation step 8.

## Decisions
1. **A per-ADR freeze gate stays local; the phase exit gates the phase.** The evidence for ADR 014
   is not the exit scenario but three small class 4 variants of `folder-inventory-to-csv`, each
   tested against `fake` and run by hand against a local model; `load-test-triage` on prepared
   data stays the phase gate. Rejected: the exit scenario as the personal gate (it holds ADR 014
   hostage to G4–G6 decisions that are not its own) and a fake-only example (synthetic evidence —
   the ADR 013 defect repeating).
2. **The output-family ADR moves ahead of ADR 014.** The operator reported the output surface weak
   already in the shipped scenarios: one flat table over all files is unreadable; wanted, a table
   per folder with the path as heading. That is the consumer evidence the G6 trigger was waiting
   for — waiting for the step 8 hand-build would rediscover what is already reported. ADR 014
   therefore stays Draft (general rule 11 holds one ADR in Implementing), and its gate variants
   profit from the output ADR without depending on it.
3. **The adapter package.** Home decided: this repository, a package beside the engine, an
   officially supported add-on; layout and productization are implementation choices. The
   protocol is the module's own decision, not the ADR's: the LM Studio API (model load and unload
   with only an installed LM Studio), the generic OpenAI-compatible HTTP (compatible local servers
   and cloud models alike), or both. The `llm` action, the provider registry and `fake` stay core
   (ADR 014 §1–§2 unchanged).
4. **Tiering mechanics.** Per-node `model` plus graph branching; a model-selecting action is
   rejected as hidden policy (ADR 014 alternative G); the deterministic middle form — a selection
   function writing a parameter that an engine-resolved `model` reads — is in Leaves open with its
   trigger.
5. The shared mechanisms are phrased in each Draft against the accepted ADRs they build on
   (ADR 013, ADR 016), never as a constraint on the other Draft (`adr-rules.md` §5).
6. Clarified in discussion, no document change: phase 2 runs `load-test-triage` on prepared
   files; the live system under test belongs to the publication gate.

## Open questions
None; the architectural input of the next session is the `result-file-composition` note.

## Next steps
1. Roadmap step 7: an `architecture` session opens the output-family ADR from the note, checking
   rule 3 (one decision or two).
2. Roadmap step 8: ADR 014 into Implementing with its gate variants, after step 7.
3. The `fix/` session for the atomic state write and the session lock, taken at any pause.

## References
- Branch: `development` — documentation only.
- Documents changed: `docs/adr/adr-014-llm-node-and-provider-adapter.md`,
  `docs/adr/adr-019-question-document-and-its-renderers.md`, `docs/adr/README.md`,
  `docs/architecture/scenarios/load-test-triage.md`,
  `docs/architecture/scenarios/repository-interview.md`,
  `docs/architecture/scenarios/README.md`, `docs/architecture/roadmap.md`,
  `docs/architecture/notes/README.md`,
  new `docs/architecture/notes/2026-08-24-result-file-composition.md`, the session registry.
- Related ADRs: ADR 014 (Draft), ADR 019 (Draft), ADR 013, ADR 016, ADR 011, ADR 006.
- Executes and revises: `2026-08-23-architecture-1` §2 (G1, G2, the G6 trigger) and its §6 order.
