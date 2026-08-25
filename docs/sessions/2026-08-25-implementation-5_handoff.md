# Session 2026-08-25-implementation-5

## Type
implementation

## Goal
Fix the action-registry twin of the provider-registry bug: `get_registered_actions_info` hands out
the live registry, so an action a plugin registers is reported as a core component.

## Completion criteria
- `get_registered_actions_info` returns a snapshot, not `ACTION_DESCRIPTIONS` itself.
- An action registered by an external module is reported under `External components` and not under
  `Core components`, proved by a test.
- The component report no longer hands a caller a dictionary whose mutation changes the registry.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- The function, validator and codec registries are untouched: they build a fresh dictionary per call
  and never had the defect.
- The provider registry keeps its fix as written.
- The help contract is untouched: it decides core against external by the defining module of the
  class, not by the loader's snapshot, and was never wrong here.
- Whether the loader should classify components at all is not decided in this branch.

## Status
`completed`

## Result
`get_registered_actions_info` returns `dict(ACTION_DESCRIPTIONS)` and says in its docstring why the
copy is the point. With that, the component loader's difference works again: an action registered by
an external module appears under `External components` and the `Core components` section holds only
what the engine ships. The same call feeds `WorkflowEngine.components` and `components_report`, so a
caller now holds a view of the registry instead of the registry itself.

Three tests in `tests/test_registration.py` cover it: a module written outside the engine package
registers an action and is loaded through `ComponentLoader`, asserting the action is reported as
external and that a core action stays core beside it, plus a unit check that writing into the
returned mapping registers nothing. All three were run against the previous code first: the two that
name the defect fail there and pass after the change.

No documentation changed. The component report is named in no document, and the core-against-external
rule that `README.md` and `docs/architecture/overview.md` do describe is the help contract's, which
was never affected.

Verification: `uv run pytest` 777 passed, `uv run ruff check .` and `uv run ruff format --check .`
clean.

## Decisions
1. **The copy is made in the registry, not at the call site in the loader.** Copying in
   `ComponentLoader` would fix the report and leave the accessor still handing the live registry to
   `components_report` and to any plugin author who calls it. What the accessor promises is what was
   wrong.
2. **A `dict` copy, not a read-only mapping.** `MappingProxyType` would state immutability in the
   type, but it changes the declared return type of a public accessor, and the loader would copy it
   again to build its difference. The provider registry was fixed with a plain copy; two twins are
   worth keeping identical.
3. **The test goes through the loader, not only through the accessor.** A test that only asserts the
   returned dictionary is a copy would pass over the actual defect, which is a report calling a
   plugin's action a core component.

## Open questions
- Two rules answer core-against-external in this repository: the loader compares registry snapshots,
  the help contract reads the defining module of the class, and `help_contract/builder.py` states in
  its own docstring that the loading path cannot answer the question — a component registered by a
  launcher script is in the registry before the snapshot is taken. They disagree for that case.
  Whether the loader should classify at all, or report a flat list and leave the question to the help
  contract, is an architecture decision and was left alone.
- `components_report` appears in no document. Whether it is a product surface or a debugging print
  left over from early bootstrap is undecided.

## Next steps
1. Roadmap step 10: build `load-test-triage` by hand on prepared data.
2. Roadmap step 11: ADR 019 narrowed into Implementing, with the `support-intake` note reformatted as
   a class 2 scenario beside it.

## References
- Branch: `fix/action-info-snapshot`.
- ADRs: none. ADR 005 owns the plugin loading this repairs; ADR 009 owns the help contract, untouched.
- Changed documents: none.
