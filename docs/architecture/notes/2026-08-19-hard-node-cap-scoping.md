# Where the hard node cap should live

- **Date:** 2026-08-19
- **Trigger:** open question carried from the operator investigation (`2026-08-18-investigation-1`) and
  restated when closing its remaining findings (`2026-08-19-implementation-1`): the default
  `hard_max_nodes_visited` of 1000 is generous for a short task flow and low for a recursive folder scan
  (~330 tree entries already trip it in a small tree).
- **Status:** open
- **Affected:** ADR 010 (session safety cap), ADR 012 (workflow inputs), ADR 007 (CLI contract),
  ADR 017 (Accepted — the per-node dimension, decided; see below)

## What exists today

ADR 010 puts the hard cap in one place: the runtime configuration field `hard_max_nodes_visited`,
default `1000` (`config_loader.py`), applying to every run and resume, not bypassable per session. The
per-session soft limit `max_nodes_visited` stays operator-controlled, and a safety stop is reported as
`workflow_paused_safety_limit`. The recovery flow was validated on a real run: the operator raises the
value in the config and resumes.

So the parameter is already visible, documented in the config file, and editable. What is unresolved is
its *scope*: one global number has to serve workflows whose natural node counts differ by an order of
magnitude.

## Phase 1 position

Freeze the current behaviour: one global config field, default `1000`, config edit plus resume as the
recovery path. No code change, no ADR. The gap is a documentation gap — the README session that adds the
template run/retrieve how-to states the cap, the symptom of hitting it (exit code 2 with
`workflow_paused_safety_limit`), and the config-edit recovery.

## Directions worth weighing later

1. **Cap declared by the workflow.** The workflow knows its own shape better than the host config does: a
   scan over an unknown tree is unbounded by nature, a three-node copy flow is not. A declared ceiling
   would live next to `inputs` and `deliverables` (ADR 012 / ADR 011 precedent for workflow-level
   declarations). Tension: the cap exists to protect the *host* from a runaway definition, so letting the
   definition raise its own ceiling weakens exactly what it guards. A workable split is that the workflow
   may lower it freely and raise it only up to a host-configured maximum.
2. **Cap derived from a workflow type.** If workflow types (or profiles: "task", "scan", "batch") ever
   enter the model, the cap becomes a property of the type rather than a number the operator maintains.
   Cost: the model has no notion of a workflow type today, so this cannot precede that decision.
3. **Keep it global and only tune the default.** Cheapest, changes nothing structurally, and only moves
   the arbitrary number. Worth doing only with real numbers from more scenarios than the one scan.

## The per-node dimension, decided

The ADR-0083 flow supplied the evidence this note's global question never had: a retry that re-enters
a question as a fresh visit is bounded by nothing but the hard cap, which means up to a thousand paid
agent rounds stopped far from the culprit (session `2026-08-20-investigation-1`). Decided in session
`2026-08-20-architecture-4` as **ADR 017**: a node may declare `max_visits`, enforced by the engine on
entry, failing under `max_visits_exceeded`, with no default — so the scan case that motivates this
note stays unbounded per node unless its author declares otherwise, and the global cap remains the
host's backstop. Business bounds (how many follow-ups a task needs) stay in flow data and are not this
mechanism.

## Open question

Is the cap a property of the host (protect the machine from any definition), of the workflow (each flow
knows its own size), or of a workflow class that does not exist yet? The answer decides whether this ever
becomes an ADR that supersedes part of ADR 010, or stays a tuned default. ADR 017 does not answer it —
the per-node cap bounds a loop inside a run, while this question is about the size of the run itself —
but it lowers the stakes: a livelock is now caught at its node when declared, so what remains for the
global number is the honest-size question, waiting on real numbers from more scenarios.
