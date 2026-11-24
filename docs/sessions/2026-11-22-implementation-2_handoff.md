# Session 2026-11-22-implementation-2

## Type
implementation

## Goal
Implement the model builder, the `report` command and the viewer of ADR 022 from the design mockup
agreed in session `2026-11-22-implementation-1`, with the home directory replaced by `~` and tests over
the model and the data block.

## Completion criteria
- The engine builds the fact model of a session through the `Storage` contract: the session and its
  ending, the definition with both views of every node and a per-node build error, the path with the
  origin of the transition each visit took, the parameters with rendered and cut values and the
  workflow inputs marked, the artifacts, the journal and the pending block of a paused session.
- In the rendered values the home directory of the machine writing the report is replaced by `~`, and
  the model and the document state that it was.
- `workflow-engine report --session-id <id>` writes one self-contained HTML document into the session
  directory, `--output` writes it elsewhere and `--no-values` leaves the values out; it answers in the
  `CommandResult` with the path of the document and changes nothing of the session.
- The viewer and its styles ship as package data, taken from the third version of the mockup without
  its sample switcher.
- Tests cover the model of a completed run with a loop, a failed run, a run paused on its budget, a
  run paused at a question, a `validators` origin and a node that cannot be built; the `~` replacement,
  the cut and `--no-values`; the data block parsed back and escaped; the command's output paths.
- `uv run pytest` and `uv run ruff check .` pass.

## Scope boundaries
- No Playwright suite, marker, dependency group or CI job: a session of its own right after this one;
  the owner checks the viewer in a browser by hand meanwhile.
- No change to `README.md`, the overview or the walkthrough: implementation session 3.
- ADR 022 is not amended; a finding that contradicts it is raised, not written into the ADR.

## Status
`completed`

## Result
- `workflow_engine.report.model` builds the fact model (`schema_version` `1`) in the shape of the
  mockup's draft, from the state view, the record stream and the definition read afresh through
  `load_workflow`; the engine gains `get_definition` and `get_session_dir` for it.
- `workflow_engine.report.document` wraps the model in the engine's shell, styles and viewer, shipped
  as package data under `report/viewer/`; the install smoke test checks that the wheel carries them.
- `workflow-engine report --session-id <id> [--output <file>] [--no-values]` is an information
  command: it writes `report.html` into the session directory by default and answers with its path.
- The viewer is the agreed third version of the mockup reduced to one session, with the `~` statement
  in its footer, the safety-cap and not-started pauses, every presentation list of a question, and
  omitted values said as such.
- `tests/test_adr022_report.py`: 25 tests over the model of the four agreed sessions plus a safety-cap
  pause, a session not started, a failing validator, a visit refused on entry and a node that cannot be
  built; the question as presented, without values and unresolved; the `~` replacement, the cut and
  `--no-values`; the data block escaped and parsed back; the
  default and `--output` paths; the session byte for byte unchanged.
- Four reports of real sessions were written outside the repository for the owner's check in a browser.
  The first showed every tab at once in one column: the mockup's page host supplied the `[hidden]`
  rule, the shipped styles did not, and a section's own `display` overrode the attribute. The rule is
  now part of the styles, a test asserts it, and the tabs, Graph first, were checked in a browser.
- At the owner's request after reading the paused question, the question is carried as presented as
  well as written, and ADR 022 §3 is amended with it; the scope boundary that kept the ADR unamended
  was lifted by the owner for this change.
- The report was written for all 401 sessions of the consumer project `payment-reconciliation` (three
  workflows, loops of up to 89 visits, an interactive pause, failures), into a scratch directory and
  never into that project: every visit's transition was decided, the two sessions whose probe node no
  longer builds degraded as designed, and one run that ended mid-way exposed the interrupted case.

## Decisions
1. **The transition a visit took is decided by replaying its guard trace** against the effective
   transitions in order — members of a group before the group, short-circuited as the engine
   evaluates — and is `null` where the trace and the definition disagree or the visit was refused on
   entry. Alternative: matching the recorded target (not chosen — a retry and an exceeded attempt
   record a target no transition names).
2. **A node that cannot be built keeps its transitions where they build without the action**, through
   `build_transitions`, now split out of `workflow_node_factory`; otherwise only the written view
   remains. Both cases state the build error.
3. **A guard reads with its members in the model** (`all_of(no_error, not is_output_exist_file)`),
   since the name a record carries for a group says nothing of what it checked; the replay uses the
   record names.
4. **The `~` replacement runs before the cut**, on the POSIX and the native form of the home
   directory, and `options.home_replaced` states it; `--no-values` writes no value and no replacement.
5. **Every `<` of the data block is written as `<`**, which covers `</` and `<!--` in one rule.
6. **Two pauses beyond the mockup** have a pending block of their own: the global safety cap and a
   session not yet started.
7. **The paused question is shown as presented, the template text on a switch** (ADR 022 §3
   amended). Its fields are resolved in Python by the ADR 016 rule against the state, which the
   paused node has not changed since it presented them; `~` is replaced in them and `--no-values`
   leaves them out, and a reference that no longer resolves leaves the written view with the reason.
   Alternatives: the template text alone (not chosen — the reader matches references by hand) and
   resolution in the viewer (not chosen — a second template rule in JavaScript, and the model carries
   no `output.` or `artifact.` values).
8. **A run entered and left with no outcome is reported as interrupted**, standing at the state's
   current node with a `resume` command; the ending is read from the outcome of the last entry
   (`run` or `resume`), so an older pause does not stand in for a later interrupted run.
9. **A node that does not build is visible without opening it**: the header names it, the drawing
   frames it in a dashed red line, the list and the legend mark it, and `build_error` carries the whole
   cause chain, since the engine's top message names no function. Asked for by the owner after
   reading a `payment-reconciliation` report whose probe function is no longer registered.

## Open questions
- The persisted codec name of a path depends on the Python version: 3.14 writes `pathlib.Path`, 3.13
  knows only `pathlib._local.Path`, so every session of `payment-reconciliation` (written on 3.14)
  fails to load on 3.13 in any read command, the report included. An engine defect outside ADR 022.
- `render_value_as_text` renders a `deque` as `deque([...])`, where the mockup's draft showed a list;
  the report keeps the engine's single rule and the rule is not changed here.
- Journal details and error messages are not values, yet a failure message can name a path under the
  home directory; ADR 022 replaces `~` only in the rendered values.
- Nested loops are still not grouped by the path view; only the first loop folds into passes.

## Next steps
1. The owner checks the four reports in a browser; corrections land on this branch.
2. A `fix/` branch for the Python-version dependence of the persisted codec name of a path.
3. The Playwright suite, its marker, its dependency group and its CI job, in a session of its own.
4. Implementation session 3: `README.md`, the overview and the walkthrough; the CI run on the branch;
   merge and freeze.

## References
- Branch: `feature/adr_022-human-readable-run-report`
- ADR 022 (Implementing)
- Changed: `docs/adr/adr-022-human-readable-run-report.md`, `src/workflow_engine/report/` (new), `src/workflow_engine/workflow.py`,
  `src/workflow_engine/engine.py`, `src/workflow_engine/cli/contract.py`,
  `src/workflow_engine/cli/main.py`, `src/workflow_engine/cli/use_cases.py`,
  `tests/test_adr022_report.py` (new), `tests/test_install_smoke.py`
