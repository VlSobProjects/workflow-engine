# Scenarios

A scenario is a task the engine is measured against: who answers each step, what data goes in, which
paths through the data are expected, and how it ends. Scenarios are written before the decisions they
need; architecture and investigation sessions find the decisions a scenario lacks.

## Classes

| Class | What it is | Where it lives |
| --- | --- | --- |
| 2 | An external task written in full, with prepared input data | `docs/architecture/scenarios/<name>.md` |
| 4 | A shipped example: its walkthrough in `examples/` carries the same header | one registry row here, pointing to the walkthrough |

The class of tasks in `docs/architecture/purpose.md` is not a scenario and does not filter work.
Synthetic end to end tests in `tests/` check nodes through a real agent; they are not scenarios and are
not evidence at the ADR freeze gate.

## Structure

A scenario has a stable identifier, the fixed header of `template.md` and a free body. The header
fields are mandatory: `Identifier`, `Class`, `Answerers`, `Input data`, `Expected paths`, `Ends with`,
`ADRs exercised`.

## Scenario and ADR

Scenario and ADR relate many-to-many. The list `ADRs exercised` in the scenario is the one truth for
the relation, because an accepted ADR cannot be edited. A new ADR names the scenario in its `Consumer`
section, and the scenario adds the ADR to its list in the same session. The freeze gate in
`docs/adr/process.md` takes its evidence from a scenario of class 2 or 4.

## Variants

One example with named variants replaces several that derive from one another. Every named variant is
covered by a test or marked as not verified in the walkthrough.

## Naming

Class 2: `<short-name>.md`, lowercase ASCII and hyphens; the identifier is the file name without
extension. Class 4: the identifier is the template name in `examples/`.

## Registry

The registry is the only index of scenarios. A row is one sentence. Add the row when the branch merges
into `development`.

| Identifier | Class | Summary | ADRs exercised | Link |
| --- | --- | --- | --- | --- |
| `repository-interview` | 2 | An agent interviews the human and creates the repository and documents that seed the consuming project's development loop | ADR 011, 013, 015, 016, 017, 018 | [repository-interview.md](repository-interview.md) |
