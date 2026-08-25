# Two drifts: what a workflow holds still inside a run, and what it holds still across authors

- **Date:** 2026-08-25
- **Trigger:** the discussion that followed session `2026-08-25-implementation-5`, on what the exit
  scenario is actually evidence of. The claim the project rests on — that precise steps, exact
  prompts and checkable conditions compress a model's nondeterminism to an acceptable distance —
  turned out to cover two different measurements that were being planned as one.
- **Status:** open
- **Affected:** ADR 014 (the model is chosen per node, and the `fake` adapter is the deterministic
  reference), ADR 021 (the record channel is where a run's route is read from), ADR 013 and ADR 017
  (the typed answer and the bounds are the mechanisms under test), ADR 011 (the deliverable that is
  judged), scenarios `load-test-triage` and `workflow-authoring`,
  `2026-08-21-agent-instruction-and-skill.md` (the instruction an answering agent is given)

## The two drifts

**Drift B — execution.** One definition, several providers. Does the run take the same route through
the graph, reach the same class of verdict, and find the same defects planted in the data? This
measures the engine: whether guards, typed answers, bounds and exact prompts hold a nondeterministic
component still enough to be operated. It needs no authoring workflow — the same definition is run
against a local model, and against two cloud vendors, without a single edit, because ADR 014 chooses
the model per node.

**Drift A — authoring.** One brief, several agents. Do they produce equivalent definitions? This
measures the authoring contracts: whether the published question blocks carry enough for a party
that does not know the engine to compose a valid graph. It needs `workflow-authoring` to exist.

They were being planned as one experiment, and they are not one. B is available far earlier than A
and is the stronger claim of the two, because it is the one that argues for a low-level engine
against the ready-made alternatives.

## How B is measured without turning into an impression

- **The `fake` adapter is the reference run.** Scripted replies give a deterministic route and a
  deterministic verdict. A model run is then a distance from a known point, not a judgement call.
- **The numbers are declared before the runs.** Did the route match the reference; did the class of
  verdict match; how many planted defects were found; how many times a reply failed to bind
  (`llm_answer_invalid`). The route comes from the record channel of ADR 021, so it is read, not
  reconstructed.
- **The boundary is a result, not an assumption.** "Which models can do this" is drawn by running
  them, and a model that fails is a data point about the required capability, not a defect.

## How A is measured, when its turn comes

- The brief is written outside the project's context and handed to each agent verbatim; the party
  that answers the domain questions is the same person for every run.
- Transcripts are kept whole. Where the agents' questions diverge, the divergence is the data — the
  authoring workflow is the invariant, the answerer is not.
- Criteria declared in advance: the produced definition validates without a run; the run completes on
  the expected path; the planted defects are found.
- The blindness of the authoring agent is a separate problem with its own note
  (`2026-08-25-role-separation-answerer-and-operator.md`).

## Open questions

The data-generation discussion (`2026-08-26-architecture-1`) answered most of this list; the
drift-B protocol now lives in the `load-test-triage` scenario body, and this note keeps only what
is still open.

- What "acceptably close" is, numerically. Still open: the concrete thresholds are declared by
  the protocol half of roadmap step 14, into the scenario's protocol section, before the measured
  runs.
- Where the results of drift-A live, when its turn comes. Drift-B results land in the notes of
  its measurement sessions — no new document class for one experiment — but drift-A brings whole
  transcripts, which a session note cannot carry.

Answered and moved out of this note: how many dataset variants — the variant map gives more than
ten declared routes (seven captures plus the derived pre-check, window-selection and
`fake`-scripted variants); the capability profile per model — the gate object is a node-to-model
map and the extended measurement substitutes models into it, so the capability boundary is read
from which substitutions hold; the content of the data generation — real captures of a real
system under test under a real load rig, conditions induced for real, derived variants by
excerpt-window selection. The map and the rationale are in the `load-test-triage` scenario and in
the session note `2026-08-26-architecture-1`.
