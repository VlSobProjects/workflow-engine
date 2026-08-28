# Assisted authoring extends to component authoring

- **Date:** 2026-08-28
- **Trigger:** external talk with an AI practitioner (2026-08-28); the objection "companies want
  agents to do everything, without frameworks" and the counter-argument built on phase 3
- **Status:** open
- **Affected:** phase 3 assisted authoring (`docs/architecture/roadmap.md`), ADR 005, ADR 009

## The idea

Phase 3 as currently framed: authoring agents write a triage-class *workflow* through the published
surfaces alone. The extension: the authoring agent also writes the *module* the workflow needs —
functions, guards, codecs — when the registered inventory does not cover the task.

The output is then a complete deterministic artifact: a workflow definition plus a component module,
both reviewable, both testable by the author once, both giving reproducible answers at run time. The
model cost is paid at authoring time, not on every run.

## Why it matters

This inverts the strongest market objection heard so far — "soon a model will do everything itself,
nobody wants frameworks". Answer: yes, let it do everything — *at authoring time*. An agent that does
the task itself is paid on every run, in inference and in non-determinism. An agent that writes the
artifact is paid once; what remains is code a human can test, and a run that can be explained and
repeated. Laziness is best served by determinism; the lazy company just has not done the arithmetic.

## Open questions

- What is the published surface for component authoring? Writing a workflow needs the operator help
  and introspection contract (ADR 009); writing a component needs the registration contracts of
  ADR 005 (decorators, naming, module loading) exposed as documentation an external agent can act on
  blindly.
- Verification story: is a test module part of the authored artifact? The claim "you test the
  generated functions yourself if needed" is stronger if the agent ships tests alongside.
- Trust boundary: authored components run in-process. A generated workflow is data; a generated
  function is code. Review before registration is the obvious gate, but the note records that the
  extension changes the risk class of the authored artifact.
- Measurement: phase 3 measures divergence between authoring agents over a JSON definition. With
  components included, divergence spans code — what is the comparable unit?
