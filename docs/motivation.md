# Motivation

This document argues why the project exists: the challenges it answers and where it applies. It is
written for a reader who follows the current AI landscape but does not know this codebase. It is not
a description of the engine — that is [`README.md`](../README.md) — and not its internal charter —
that is [`architecture/purpose.md`](architecture/purpose.md), which states the method, the boundaries
and what counts as done.

Growth rule: this document is a fixed set of challenges with one answer each. A new argument merges
into an existing answer or replaces one; it is not appended.

## The starting point

The current default for automating a complex task is to hand it whole to an agent: a large model, a
prompt, a set of tools. It works impressively in a demo and poorly as automation, because somebody
sits and watches what the agent does — and given the whole task in one context, the model takes a
different path every time. The origin of this project was exactly such a task, load-test triage,
where the attempt to automate it with an agent turned out to be supervision, not automation.

The claim of the project, in one sentence:

> Deterministic code does the work, guards check every boundary, and a model is called only where
> judgment is needed — the smallest model that can do it.

Automation deserves the name only when a run can be explained and repeated. The full argument is in
[`architecture/purpose.md`](architecture/purpose.md); everything below answers the objections raised
against it.

## The challenges

### "Companies just want agents to do everything — no framework needed"

This is a statement about buying, not about engineering: magic is easier to sell than a method. The
answer is economic. An agent that does everything is paid for on every run, forever — inference cost
plus non-determinism cost, because nobody can promise the next run takes the same path. An authored
workflow inverts that: the expensive model is paid once, at authoring time, and what it produces is
an artifact — a workflow file, functions, guards — that can be reviewed and tested once and then runs
cheap and reproducible for as long as it is needed. The roadmap makes this concrete: in its assisted
authoring phase an agent writes the workflow through the published surfaces, and the divergence
between authoring agents is measured, not assumed. AI helps write the workflow; the workflow does not
need AI to be trusted at run time.

### "Models are getting better — a planning agent will solve this"

Model quality is not the constraint; accountability is. However good the planner, the result is only
usable as automation if its boundaries are enforced and its checks are code, because that is what
makes a run explainable and repeatable — and explainability does not improve with model size. A
better model makes a better author, and the project welcomes that: assisted authoring turns "an agent
will write the workflow" from a hope into a measured experiment.

### "Isn't this just n8n / LangGraph / a classic orchestrator?"

The field converged on the same shapes — nodes, state, actions — which suggests the decomposition is
right. The difference is deliberate and sits at the boundaries. GUI platforms let you draw a graph
and then hand the nodes to agents: you still do not control what actually happens inside a step.
Code-first frameworks are libraries an agent is embedded in, where the boundaries are a convention
the developer maintains. Here the boundary is the engine's contract: a model step physically receives
only what its subtask declares — enforced by the engine, not by the model's discipline. And unlike a
classic orchestrator, the next node is chosen at run time from the data the previous nodes produced.

### "A model could do what your complex function does — where is the line?"

Determinism is required of the boundary, not of the step. A step may be a model with a prompt; its
answer is normalized by a function and then routed by deterministic guards, so the transition is
deterministic over the normalized output no matter who produced it. That turns "function or model"
from an architectural dilemma into a reversible engineering trade-off: a function is testable and
free to run but expensive to write against messy input; a model is cheap to author but paid on every
run. Start with the model, journal its real inputs and outputs, and the journal becomes the
specification of the function that later replaces it — measured on the same data.

## Where this matters

- **Investigation-shaped work** — triage, diagnosis, incident analysis: tasks where the next step
  depends on what the previous one found, most steps are deterministic fetching and filtering, and
  judgment is needed only at a few branching points. This is the origin domain.
- **Organizations that cannot send data to the cloud** — small and mid-size firms bound by contract
  or regulation. Critical data is processed only by local models, and the model never has direct
  access to a database: a function exports exactly what a step needs and nothing else.
- **Regulated decisions** — domains where "an agent decided" is not an acceptable audit answer. A
  journaled, repeatable run with enforced step boundaries is a compliance property there, not a
  feature. One principle, two consequences: the same mechanism that makes a run explainable is what
  makes it safe for sensitive data.

## What this is not

Not a chat framework, not an agent framework, not a planner: the engine runs the graph its author
wrote and never invents a step. A situation the author did not foresee ends the run with a handover
to a human, carrying the collected evidence and the reason it stopped. The boundaries are stated
precisely in [`architecture/purpose.md`](architecture/purpose.md).
