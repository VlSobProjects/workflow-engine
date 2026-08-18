# ADR 012: Workflow input parameters

## Status
Draft

## Active branch
—

## Context

Phase 1 is defined by the criterion "the engine core is usable in different user scenarios". Today
the only way to vary a run is to edit the workflow JSON by hand: the shipped templates carry a
placeholder token that the operator replaces mechanically before every session (with the UTF-8 BOM
encoding trap on Windows recorded in the 2026-08-18 investigation). The `resume` operator-output
flags (`--param-name/--param-value/--write-mode`) looked like a parameter path but are broken
(`WriteParamMode` crash), are absent from the frozen ADR 007 command contract, and feed the
interactive-input mechanism that ADR 007 §4 explicitly defers to phase 2.

Two architectural stances were discussed:

1. A workflow file is a reusable definition; run-specific values are bound to the session at
   creation time.
2. A workflow file is a single-run object with its values baked in; reuse happens through a
   separate template entity that generates workflow files, and runtime input arrives through an
   interactive action in phase 2.

The current architecture already contains both halves: the operator's workflow file is a reusable
source, and every session snapshots its own copy into storage (ADR 003/004). The missing piece is
binding values at session creation without editing the file.

Constraints:
- ADR 006 bus invariants hold: parameters live in the engine-managed flat bus, every write is
  applied through the engine and journaled, resume is deterministic from persisted state.
- ADR 007 result-shape stability: extension of the CLI contract is additive only.
- Parameter values must keep their Python types across save and load, which the codec round-trip
  (ADR 006) already provides.

## Decision

A workflow declares its input parameters; the operator binds typed values to a session before its
first node runs; the engine validates, applies and journals the bindings. Stance 1 is chosen: the
workflow file stays reusable, and no separate template entity is introduced.

### 1. `inputs` declaration in the workflow definition

- The workflow definition gains an optional top-level `inputs` block: an ordered list of input
  declarations, each carrying `name`, optional `type` (a registered codec type name), `required`
  (default `true`), and optional `description`.
- The declaration is the input interface of the workflow — the mirror of `deliverables` (ADR 011)
  on the input side. It states *what* the workflow needs, never the concrete values.
- Build-time validation covers shape only: a list of unique non-empty names; a declared `type`
  must name a registered codec.
- The declaration is introspectable: it surfaces through the CLI result data and the ADR 009 help
  contract.

### 2. `set-input`: binding values to a session

- New CLI command `set-input`: binds one or more input values to an existing session in a single
  invocation. Each assignment carries the input name, the value as text, and optionally a codec
  type name.
- `set-input` accepts only names declared in the session's `inputs` block. An undeclared name is a
  command error.
- Binding is allowed only while the session has visited no node. A session whose run has started
  rejects `set-input` as a command error; mutating the bus of a started run from outside stays
  forbidden.
- Applied values land in `state.params` as `SET` writes through the engine's normal write path,
  and the binding is journaled as an operator session event, per the ADR 006 auditability
  requirement for external engine calls.

### 3. Typed values through codecs

- A value arrives as text: a raw string, or JSON for structured values (lists, dicts).
- When a codec type is known, the text is decoded through the registered codec into its Python
  type (for example `pathlib.Path`, `collections.deque`) — the same round-trip contract session
  parameters already use, so a bound input is indistinguishable in state from a parameter written
  by a node.
- The codec is resolved with this precedence: the explicit type in the assignment, else the `type`
  declared in `inputs`, else the value stays a plain string. When both are present they must
  agree.
- Codec type names are the operator-facing vocabulary and are discoverable via `help-components`.

### 4. One-shot form on `run`

- `run` accepts the same repeatable assignment option, applied between session creation and
  execution, so a fully parameterized non-interactive run is one command. `init-new-session` gains
  nothing: the two-step flow is `init-new-session`, then `set-input`, then `resume`.

### 5. Enforcement at start

- Starting a session (first execution only) with a `required` input unbound is a setup error: the
  run fails before any node executes, with the missing names reported, following the ADR 006
  setup-error journaling semantics and the ADR 007 exit code `4`.
- Optional inputs may stay unbound; reading an unbound parameter keeps its existing ADR 006
  semantics.

### 6. The uncontracted `resume` flags are removed

- The `resume` operator-output flags (`--input`, `--error-code`, `--error-msg`, `--param-name`,
  `--param-value`, `--write-mode`, `--artifact-name`, `--artifact-path`,
  `--artifact-description`) are removed from the v1 parser. They fabricate the output of the
  current node — the interactive-answer mechanism that ADR 007 §4 defers to phase 2 — and are
  broken today. This belongs to this decision because it makes the input binding above the single
  operator parameter path of v1; the phase-2 interactive-input ADR reintroduces its own surface
  deliberately.

## Alternatives considered

### A. Keep template-token replacement in JSON
Pros: nothing to build.
Cons: manual file editing per run with encoding traps; no validation, typing or audit; the phase 1
criterion is met only formally. Rejected.

### B. Fix and contract the `resume` output flags as the input path
Pros: one-line fix away from "working".
Cons: wrong semantics — the operator substitutes a node's output, which is the interactive-answer
mechanism, not an input binding; requires a placeholder node, a mandatory `--input`, and the
two-step flow for every parameterized run; one untyped parameter per call; freezes a shape that
the phase-2 interactive work would have to supersede. Rejected.

### C. Interactive input action as the only mechanism (stance 2, phase 2)
Pros: architecturally pure — all bus writes keep coming from node outputs; the engine model
already has `PresentResponse`.
Cons as the sole mechanism: a parameterized non-interactive run becomes impossible by design —
every parameterized workflow must pause and be resumed, which contradicts the ADR 007 automation
orientation; parameter variation for scripts falls back to generating JSON. Deferred to phase 2 as
the complementary mechanism for mid-run input, not chosen as the input path.

### D. Template entity generating workflow files
Pros: clean separation of reusable template and single-run instance.
Cons: a new subsystem (template storage, instantiation, versioning, validation of substitutions)
that no current scenario requires — every known case is the same graph with different values; can
still be layered on top of declared inputs later if structural variation ever appears. Rejected
for phase 1.

### E. Declared inputs with typed pre-run binding (chosen)
Pros: the workflow file stays reusable as-is; typed, validated, journaled input with both a
one-shot and a prepared-session flow; the input interface becomes introspectable.
Cost: schema block, one command, one repeatable option, an operator session event, start-time
validation, parser cleanup.

## Consequences

Enables:
- A template plus `run` with assignments plus `--export-dir` covers a full user scenario in one
  non-interactive command; the two-step flow serves prepared sessions.
- Workflow files are shared and reused without editing; the BOM trap disappears from the operator
  flow.
- Tooling reads what a workflow needs (`inputs`) and what it produces (`deliverables`) without
  running it.
- Missing required inputs fail at setup time with a precise message, not mid-graph.

Costs:
- The workflow schema grows a second declarative block with build-time validation.
- The CLI grows one command and one repeatable option; the engine grows a binding API, a start-time
  check and an operator session event code.
- Codec type names become part of the operator-facing contract for inputs.

Closes off:
- Writing parameters into a session after its first node visit stays impossible from the CLI;
  mid-run input remains the domain of the phase-2 interactive action.
- Undeclared input names are rejected; a workflow without an `inputs` block accepts no bindings.
- The `resume` operator-output flags leave the v1 surface; interactive input returns only under
  its own phase-2 ADR.

## Related ADRs

- ADR 006 data flow between nodes (Accepted): the bus, the write/journal path and the codec
  round-trip this decision reuses.
- ADR 007 CLI contract (Accepted): command surface, exit codes, additive-extension rule, and §4
  deferring interactive input to phase 2.
- ADR 009 operator help contract (Accepted): `inputs` and the new command surface through it.
- ADR 011 artifact addressing and export (Accepted): `deliverables`, the output-side mirror of
  `inputs`.

## Implementation notes

To be refined when the ADR moves toward Implementing. Current sketch:

- Assignment syntax candidate: a repeatable option, one assignment per occurrence, carrying
  `name`, optional codec type name, and the value text (exact argparse shape to be settled; it
  must allow several assignments in one invocation and values containing `=` and spaces).
- Decoding: parse the value text as JSON when the target codec's serialized form is structured,
  otherwise pass the raw string to the codec (`CODEC_REGISTRY` lookup via
  `get_codec_by_type_name`, decode via `value_from_dict_obj`). No codec means the value stays a
  string.
- Engine API: one method that validates names against the definition's `inputs`, applies
  `ParamWrite(mode=SET)` per value through the existing write path, and records an operator
  session event (e.g. `INPUTS_SET`) with the bound names in `details` (values are already
  persisted in `state.params`; the event records names, not values).
- The "no node visited" guard checks the persisted visit counters of the session.
- Start-time check: on the first execution of a session, unbound `required` inputs fail setup
  before node execution, journaled per the ADR 006 `workflow_setup_failed` semantics with the
  missing names in details; exit code `4`.
- Parser cleanup: the `resume` flag block and `_output_node`/`_get_parameters`/`_get_artifacts`
  in `cli/use_cases.py` are removed; `get_all_modes_help` and the `WriteParamMode` enum stay — they
  serve the engine-internal write modes and the future phase-2 surface.
- Help contract: `inputs` joins the definition surfaces additively (ADR 009 stability rules).
- Test surface: schema validation of `inputs`; binding matrix (declared/undeclared name, typed
  decode for `pathlib.Path` and a collection type, agree/disagree between declared and explicit
  type, rejection after first node visit, exit codes); required-unbound setup error; e2e — the
  folder-inventory template run parameterized by a bound scan root and exported with
  `--export-dir`; absence of the removed `resume` flags.

## Change log

- Draft opened from the 2026-08-18 phase 1 readiness architecture session: stance 1 (reusable
  workflow, session-bound inputs) chosen over a single-run workflow with a separate template
  entity; typed multi-parameter `set-input` chosen as the two-step binding form.
