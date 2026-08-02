# ADR 001: Exception architecture

## Status
Draft

## Active branch
None

## Context

The engine reports failures inconsistently, and the current structure makes good reporting impossible.

- The seven exception types in `exceptions.py` all derive from `Exception` directly. There is no common
  root, so callers cannot catch engine failures as a group. This is why `sart_engine` uses a blind
  `except Exception`.
- Around forty raw `TypeError`, `ValueError` and `KeyError` are raised across nine modules. They are not
  part of the vocabulary of the project and cannot be handled by type.
- Configuration checking is split across two places that disagree with each other. `_load_workflow_nodes`
  builds every node, and therefore validates actions, before the protected section of `sart_engine`, so a
  configuration error escapes the engine instead of becoming a response. `_workflow_nodes_errors` does the
  opposite and collects errors, but only for transitions, only for `WorkflowError`, and only after node
  construction already succeeded.
- Only `RuntimeParameterError` carries structured context. Every other type carries a flat message, so a
  failure deep in decoding cannot say which node or which field it came from.

Two kinds of failure need different treatment.

- Configuration failures come from a workflow definition supplied from outside. They should all be
  reported before the workflow starts, and each one should name the node, the field and the reason.
- Runtime failures happen while the workflow executes and belong to the response returned to the caller.

## Decision

Introduce one exception root for the engine and split the hierarchy by phase: configuration errors and
runtime errors.

Attach context by enriching an error as it travels up. A low level check raises a precise but anonymous
error, such as expecting a string and receiving an integer. Each layer that has context catches it and
adds its own frame: the field, then the node, then the workflow. The result names the exact location
without passing a path through every decoding function.

Collect configuration errors rather than stopping at the first one. Validation of the workflow definition
gathers every enriched error and reports them together before execution starts.

Replace the raw `TypeError`, `ValueError` and `KeyError` raises with the project's own types, so that the
blind `except` in the engine can be removed.

## Alternatives considered

### A. Pass the location down into every check
Each decoding function takes the path it is validating and reports it directly.
Precise and simple to follow, but it changes the signature of every validation function and repeats the
location at every call site.

### C. Validate in a separate pass before construction
A validator walks the workflow definition, collects all problems, and construction then works on data that
is known to be valid.
Produces the most complete and most precise messages, but the schema is then described in two places,
which is the largest amount of work and the easiest to let drift.

### B. Enrich while the error travels up
Chosen. Keeps the decoding functions free of location arguments and builds the location from the layers
that already know it. The cost is discipline: every boundary that owns context has to catch and enrich,
and a missing boundary silently loses precision.

## Consequences

- Callers can catch engine failures by category instead of catching everything.
- Configuration problems are reported before start, all at once, with the node and field named.
- Every layer that owns context gains a small amount of error handling code.
- Existing call sites that rely on `TypeError` from the models will need to change.
- The blind `except` in `sart_engine` can be narrowed once the hierarchy exists.

## Related ADRs

None yet. The planned work on shared validation utilities depends on this decision, because the decoding
helpers cannot be unified before the shape of their errors is settled.

## Implementation notes

Open points to settle during implementation:

- Where the aggregate of configuration errors is produced, and whether it is one exception carrying many
  entries or a collection returned by a validation call.
- Whether node construction moves inside the protected section of `sart_engine`, or configuration is
  validated before construction begins.
- `_workflow_nodes_errors` currently overwrites the entry for each node and resets its counter inside the
  loop, so it can report only one error per node. Its shape will change with this decision.

## Change log

- Draft created. Option B chosen for context propagation after comparing it with A and C.
