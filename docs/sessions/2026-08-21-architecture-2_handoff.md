# Session note

## Type
architecture

## Goal
Settle where the final, process-specific step of the ADR-0083 scenarios belongs — the core or a
plugin — and replace the obsolete justification the coverage note carried for it.

## Completion criteria
1. The alternatives for the `S` step are stated with their costs, and the chosen one is recorded with
   an argument that does not depend on the reason ADR 014 made obsolete.
2. `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md` carries the settled argument in
   its table row, its missing list and its friction entry, and its `Affected` header is reconciled.
3. The notes registry row matches the note.
4. It is stated whether this needs an ADR, and why.
5. This session note is completed and committed.

## Scope boundaries
- No plugin is written: the consuming project decides how its own step is taken.
- No core component is added, and no ADR is opened.
- Recovery after a crash stays out (recovery note (a)); only the already-working pause and
  continuation of an interview is recorded.
- Moving the scenario into `examples/` is code work and belongs to its own session.

## Status
completed

## Result
The step stays outside the core, as a registered function in the consuming project's own module, and
the coverage note now carries the argument for it: the accumulation format is universal and the
engine's business, the protocol of what happens next belongs to the receiving side. The two
alternatives weighed against it — a core `run_script` permitted through the engine configuration in
the ADR 014 §3 shape, and a narrow core egress over `urllib` — are recorded with the reason each
lost. The note gained a section stating what an interrupted interview already carries, and the
registry row and the `Affected` header were reconciled. No ADR and no code.

## Decisions
1. **The final specific step is a plugin, not a core component.** What a flow accumulates (`dict`,
   `list`, `list` of `dict`) is universal and already carried by the core, including its rendering
   into an exported deliverable; what consumes it — a database row, an endpoint, a set of files in a
   receiver-defined format — is the other side's protocol. A core component could only be one
   integration among many, against general rule 9, or a bare process runner whose content is a
   command line from the definition.
2. **The previous justification is retired.** "Shipping it outside exercises the ADR 005 external
   module path" is spent: ADR 014 §2 gave that role to the OpenAI-compatible provider adapter. The
   trust framing is retired too — trust is real but belongs to the plugin author and to the
   operator's `external_modules` entry, not to a property of a bare install.
3. **No ADR.** The decision adds nothing to the architecture and changes no contract: it declines a
   core component. The note is the durable record; the precedent for component-level work without an
   ADR is `append_to_param`.
4. **The first client of the plugin model is the external ADR-0083 project**, which receives the
   engine and the "Writing a custom function" instructions rather than a component — ahead of the
   ADR 014 reference adapter.
5. **The interrupted interview is not on the missing list.** A paused question already survives the
   answerer leaving: `resume` without an answer re-presents it and consumes neither an attempt nor a
   visit (ADR 013 §6), and the returning answerer pulls its context through the ADR 018 surfaces. The
   accumulated parameter is both the interview record and the payload of the final step, which is the
   same fact the plugin decision rests on.

## Open questions
1. The transcript question stays open where ADR 018 left it: the engine keeps no record of the
   exchange itself, so a returning answerer reads what the flow accumulated, not what was asked.
   Nothing in these scenarios forces it yet.
2. The in-graph budget checkpoint (friction 2) and the guard that would read the pending writes of
   the current output are unchanged and still open.

## Next steps
1. Move the scenario flow into `examples/` as a shipped template: its final step is already the core
   `dict_list_to_pretty_table` deliverable, so it needs no plugin to be complete. The definition is
   inline in `tests/test_adr0083_scenario.py` today; loading it from `examples/` instead would let the
   existing tests prove the shipped file. Own session, own branch, and it must also answer how an
   interactive template is documented in `README.md`, where every example so far runs without pausing.
2. ADR 014 to Implementing when implementation starts (unchanged from the previous session).
3. Recovery note (b), retry/backoff by error class, stays the next ADR after 014.

## References
- Branch: `development` (architecture notes and their registry, per `docs/processes/git-workflow.md`)
- Subject: `docs/architecture/notes/2026-08-19-adr0083-scenarios-coverage.md`
- Changed: that note, `docs/architecture/notes/README.md`, this note
- Related: ADR 005, ADR 013 §6, ADR 014 §2 and §3, ADR 015, ADR 018
- Previous session: `2026-08-21-architecture-1_handoff.md`
