# ADR 010: Session safety cap and unbounded run policy

## Status
Implementing

## Active branch
`feature/adr_010-session-safety-cap-and-unbounded-run-policy`

## Context

`max_nodes_visited` currently acts as a per-session soft limit and supports `0` as "no soft limit".
This is useful for long runs, but it leaves a risk: a cyclic workflow can run indefinitely when the
operator starts with `0`.

For phase 1 test release, the engine needs a cheap and deterministic safety mechanism that prevents
accidental unbounded runs while preserving operator control for diagnostics.

This ADR is optional for phase 1 scope and can be accepted together with ADR 007 implementation if needed.

## Decision

Introduce a global hard safety cap and define its relation to the existing soft limit.

1. Global hard cap:
   - new configuration field: `hard_max_nodes_visited`;
   - default value: `1000`;
   - applies to every run and resume path.
2. Soft limit remains:
   - `max_nodes_visited` remains operator-controlled per session;
   - `0` keeps its meaning: no soft limit.
3. Effective stop condition:
   - run pauses when either soft limit (if non-zero) or hard cap is reached;
   - hard cap cannot be bypassed by per-session commands.
4. Operator override policy:
   - exceeding default hard cap is allowed only by explicit configuration change before run;
   - no implicit runtime auto-escalation.
5. Diagnostics on safety stop:
   - emit a dedicated event code (`workflow_paused_safety_limit`) with current node and counters;
   - preserve sufficient state to inspect likely loop chains.

## Alternatives considered

### A. Keep soft limit only
Pros: no additional logic.  
Cons: accidental unbounded runs remain possible with soft limit `0`.

### B. Add timeout-based stop only
Pros: independent from graph size.  
Cons: unstable across hardware/load; weaker for deterministic testing.

### C. Hard cap + existing soft limit (chosen)
Pros: deterministic, cheap, operator-controlled via explicit config.  
Cost: one new config field, event code, and command/UI messaging.

## Consequences

- Engine stop reasons gain one additional normalized code.
- CLI needs explicit messaging that soft unlimited mode is still bounded by hard cap.
- Config documentation must expose the default and override mechanism.

## Related ADRs

- ADR 006 data flow between nodes (Accepted).
- ADR 007 CLI contract and session lifecycle for v1 (Accepted).
- ADR 008 runtime directory and default path policy for v1 (Accepted).

## Implementation notes

Planned branch when status moves beyond Draft:
- `feature/adr_010-session-safety-cap-and-unbounded-run-policy`

Minimum implementation slice:
- config parsing for `hard_max_nodes_visited`;
- effective-limit check in engine loop;
- session event and response branch for hard-cap stop;
- tests for soft=0 + hard-cap stop and for explicit hard-cap override.

## Change log

- Initial draft opened from phase 1 architecture planning session as optional phase 1 decision.
- Moved to Implementing and opened the implementation branch.
- Implemented the minimum slice: `hard_max_nodes_visited` config field (validated as a positive
  integer, no unlimited value), the engine-loop check after the soft-limit check, the
  `workflow_paused_safety_limit` engine event mapping to the paused status, and CLI messaging for
  `set-limit 0`. The cap is read from the current configuration on every run and resume and is not
  persisted per session; a `storage_dir` change in the edited configuration does not affect an
  existing session (ADR 004), which is fixed by a regression test.
