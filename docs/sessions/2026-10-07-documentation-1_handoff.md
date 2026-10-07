# 2026-10-07-documentation-1

## Type
`documentation`

## Goal
Write the class 2 scenario `payment-reconciliation` — the reconciliation of payment documents against
bank statements that the desk letter EX-17 (2026-10-05, questions on a reconciliation POC built on
workflow-engine) describes — and answer the letter's seven questions from it.

## Completion criteria
- `docs/architecture/scenarios/payment-reconciliation.md` exists with the full template header, the
  flow shape, what ships in the core and what ships in the POC's external modules, the evaluation
  contour, the expected paths and the open decisions.
- Every statement about what the core supports is checked against `help-components`, the overview
  and the README, not recalled.
- Outside the repository: the answer to EX-17 is a `draft` on the desk, one answer per question,
  citing the scenario as the document the letter landed in.
- The branch is merged into `development`; the scenarios registry and the sessions registry carry
  their rows; `What it changed` of EX-17 names the document and the commit.

## Scope boundaries
- The roadmap is not edited. Whether this scenario replaces the load-rig run as the publication
  gate is an architecture decision for an `architecture` session in critical mode.
- No code changes, no ADR changes, no note changes.
- The POC project's own documents are written in its own repository, not here.
- No letter is released: the status and the release date belong to the user.

## Status
`completed`

## Result
- `docs/architecture/scenarios/payment-reconciliation.md`: the second class 2 scenario with a human
  in the loop and the first with a per-document loop, a certain/scored split enforced by guards, and
  an evaluation contour outside the engine.
- The measurement against the core: the shape fits; the gaps are a numeric-threshold validator, the
  fail-closed guarantee, a browser step that must outlive the paused process, and the vision channel
  for image amounts — all recorded as open decisions in the scenario.
- The draft answer to EX-17 on the desk, seven answers, with the window cut and the publication list.

## Decisions
- The scenario is a document of this repository (class 2) because it is a task the engine is
  measured against; the POC that implements it is a consumer with its own repository, the same
  split the exit scenario makes with the load rig and the system under test.
- The evaluation harness lives in the POC, not in the engine: the engine records a run, it does not
  judge one (`purpose.md` boundaries).
- Sizes in the answer are stated as small/medium/large with a sentence each, not as dates: the letter
  asked for an assessment and the window depends on the firm's back office, which nobody has seen.

## Open questions
- Whether a fail-closed guarantee belongs in the core as a provider allow-list (a sixth provider key,
  which ADR 014 refuses today) or stays a test the POC owns.
- Whether a numeric comparison guard enters the core, or stays a registered validator of the POC.

## Next steps
1. The user releases the draft answer to EX-17 on the desk.
2. An `architecture` session decides the publication gate: this scenario against the load-rig run,
   with the roadmap row rewritten and `2026-08-19-installation-and-distribution` reread.
3. The POC repository is created from this scenario; its first session writes the data generator.

## References
- Branch: `docs/payment-reconciliation-scenario`
- Changed: `docs/architecture/scenarios/payment-reconciliation.md` (new), this note
- Outside this repository: the desk letter EX-17 and the draft answer to it
- Related: `docs/architecture/scenarios/load-test-triage.md`, the note
  `2026-08-19-installation-and-distribution`, the note `2026-08-28-rendered-panels-as-model-input`,
  the note `2026-08-19-hard-node-cap-scoping`
