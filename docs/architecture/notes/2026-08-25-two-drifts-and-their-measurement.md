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

- What "acceptably close" is, numerically. Without a threshold declared beforehand, both experiments
  degrade into impressions.
- How many dataset variants are needed before a route match means anything.
- Whether a capability profile per model — context window, reliability of a structured reply, cost —
  belongs beside the results.
- Where the results live. A scenario body is not a lab notebook, and `documentation-rules.md` admits
  no report document; this may be what forces the question.
- Generating the data is a task of its own and is the long pole of both experiments: metrics of the
  test run, logs of a fictional service, resource metrics of its host, in a volume that makes triage
  a real problem rather than a demonstration. Roadmap step 14 now carries it, opened by the
  data-generation discussion (`2026-08-25-documentation-2`); what stays open here is the content
  of that discussion, not its place.
