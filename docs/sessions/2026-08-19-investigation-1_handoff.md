# Session note

## Type
investigation

## Goal
Audit the architecture documentation, the README and the repository state against the code before
the phase 1 release (merge `development` into `main`, tag `v0.1.0`), and record every finding as a
fact so it can be fixed deliberately and mined for preventive rules.

## Completion criteria
1. Tests and linter are run on `development` and the outcome recorded.
2. `docs/architecture/overview.md` is checked claim by claim against `src/workflow_engine/`.
3. `README.md` is checked against the CLI, the config loader, `examples/` and `pyproject.toml`, with
   the documented flows actually executed.
4. ADR files, the three registries (ADRs, sessions, notes), the process documents and the document
   map are checked for consistency.
5. Every finding is recorded here, classified by severity, with a file reference. No fix is applied.

## Scope boundaries
- Investigation only: no code, documentation or registry change other than this note.
- The release itself (merge and tag) is not performed here.
- Rules to prevent the recorded classes of defects are not written here; that is a follow-up.

## Status
completed

## Result
Verification on `development` at `48199a3`: `uv run pytest` — 241 passed; `uv run ruff check .` —
clean; `uv run ruff format --check .` — 185 files already formatted. Working tree clean; `development`
equals `origin/development`; `main` is 165 commits behind and contains nothing not in `development`.
No tag exists yet; `pyproject.toml` version is `0.1.0`, so the first tag is `v0.1.0`.

Every command sequence in the README was executed from a fresh directory outside the repository
(step-by-step `init-new-session` / `set-input` / `resume`, one-shot `run --input`, `export-artifact`,
`run --export-dir`, hard cap lowered via `--config` → exit 2, missing workflow file → exit 4, custom
function via a launcher script and via `external_modules` with `PYTHONPATH`, `help-component` on it).
All observed outputs, keys and exit codes match the README text, with the exceptions listed below.

### A. Blocking before the tag
1. Eight session notes exist on disk but have no row in the sessions registry
   (`docs/sessions/README.md`); 49 files, 43 registered. Missing: `2026-08-11-architecture-1`,
   `2026-08-11-architecture-3`, `2026-08-11-architecture-6`, `2026-08-11-architecture-7`,
   `2026-08-11-implementation-1`, `2026-08-18-implementation-1`, `2026-08-18-implementation-2`,
   `2026-08-18-implementation-3` (all `completed`; ADR 007–009 work). Per the registry rule an
   unregistered session is effectively lost.
2. README `flatten-copy-tree` how-to (README.md:77-84) does not state that `target_dir` must be an
   existing directory. Observed: with a non-existent `target_dir`, `copy_file`
   (`src/workflow_engine/actions/base_functions.py:53-59`) treats the path as a file target, every
   source file is copied over one file named like the directory, the run completes with exit 0 and
   `copy_report.csv` lists the same `Copied` path for every row. Silent data loss with a success exit
   code. Documentation fix is the minimum; the behaviour itself is a code defect (`fix/` branch).

### B. `docs/architecture/overview.md` — imprecise or missing facts (no false behaviour claims)
1. overview.md:125 — `copy_artifact(source, target, target_path, allow_overwrite)`; the registered
   signature is `copy_artifact(source_artifact_name, target_artifact_name, state, target_path=None,
   allow_overwrite=False)` (`src/workflow_engine/actions/create_artifact_functions.py:114-123`). The
   parameter names are what an operator writes in `function_parameters`.
2. overview.md:59-60 "a guard never receives the state" contradicts overview.md:64-65 (guards resolve
   `param.`/`output.`/`artifact.` references). Code: `BaseGuard.check(output, state, trace)`
   (`src/workflow_engine/transition/guards.py:39,49`). The guard object receives a read-only state
   view; only the registered predicate function does not.
3. overview.md:72 "nothing of `validators` survives into the runtime node": `WorkflowNode.config`
   still carries the raw `validators` list (`src/workflow_engine/workflow.py:14,45`,
   `src/workflow_engine/models/node.py:19,30`); only the transitions no longer reference it.
4. overview.md:105-106 `WorkflowArtifact` listed as (relative path, description); it also persists
   `created_at` (`src/workflow_engine/output.py:13-16`).
5. overview.md:242-243 action detail payload omits `execution_mode`
   (`src/workflow_engine/help_contract/models.py:130-138`).
6. State section (overview.md:92-101) omits `artifact_events` (`ArtifactEvent`, codes
   `artifact_overwritten` / `artifact_path_conflict`), `error_code`/`error_msg`,
   `max_nodes_visited`/`nodes_visited`, and identity fields `timestamp`, `flow_id`, `schema_version`,
   `session_id` (`src/workflow_engine/models/state.py:452-470`). `artifact_events` is a persisted,
   user-visible structure not mentioned anywhere in the overview.
7. Config discovery (overview.md:192-201) omits the `platformdirs.user_config_dir()/.workflow-engine/
   workflow_engine_config.json` lookup and the auto-creation of a default config
   (`src/workflow_engine/bootstrap/config_loader.py:75-87,205-206`); the README documents both. Also
   unstated: `--storage-dir` alone ignores config `work_dir`, and `--work-dir`/`WE_WORK_DIR` ignores
   config `storage.storage_dir` (`config_loader.py:117-120,139-140`).
8. overview.md:199 does not state the default storage directory `<work_dir>/json-storage/`
   (`config_loader.py:140,147`).
9. overview.md:205 omits `init-new-session --max-nodes-visited` (`src/workflow_engine/cli/main.py:
   123-128`); `set-limit` refusing to lower the limit below the current count unless `0`
   (`src/workflow_engine/engine.py:483-487`) is not described.
10. overview.md:51 "failure of the node, under a code": an `errors` transition without `fail` yields
    `FailTarget(code=None)`, which keeps the action's own error code
    (`src/workflow_engine/transition/base.py:54-58`, `engine.py:98-101`).
11. overview.md:44-45 describes the interactive exchange (`PresentResponse`, resume with a result);
    the engine supports it (`engine.py:437-439`) but no CLI path passes an output on `resume`
    (`src/workflow_engine/cli/use_cases.py:95`), `ActionNodeOutput.from_args` is unused and no core
    action subclasses `BaseInteractiveAction`. True of the engine, unreachable for an operator.

### C. README.md
1. README.md:202 `pytest` bare; every other command uses `uv run`; `CLAUDE.md` says `uv run pytest`.
2. `help-components` lists the `Path` codec as `pathlib._local.Path` (Python 3.13 module path) while
   README and examples use bare `Path`; bare names resolve via `resolve_codec_by_type_name`
   (`src/workflow_engine/registry/type_registry.py:104-125`). Not wrong; a reader scanning
   `help-components` for the codec name sees the long form. Related to the open note
   `docs/architecture/notes/2026-08-18-adr012-deferred-questions.md`.
3. Finding A.2 above.

### D. ADRs and process documents
1. Stale status labels in frozen ADR text: ADR 007 (`docs/adr/adr-007-...md:110-112`) lists ADR 008,
   009, 010 as "(Draft)"; ADR 008 (`:75`) lists ADR 007 as "(Draft)". Wording "Planned branch when
   status moves beyond Draft" remains in ADR 007:116, 008:79, 009:157, 010:69.
2. Template deviations: `## Active branch` missing in ADR 008, 011, 012; ADR 010 has
   `## Implementation` instead; empty value written as `—` in some ADRs and `None` in others (002,
   003). ADR 005 has an extra section `## Deferred extension: entry-point discovery`. ADR 010 and 012
   change logs have no "frozen as Accepted" entry.
3. Registry `Depends on` for ADR 003 is `—` while the file lists ADR 001 and 002 as related.
4. `docs/adr/process.md:56` ("a Draft ADR is written directly on `development`") contradicts
   `docs/processes/git-workflow.md:9-10`, which allows direct commits to `development` only for status
   changes, registries, notes and trivial corrections.
5. `docs/processes/git-workflow.md:26` example `feature/adr_007-state-codecs` does not correspond to
   ADR 007 (CLI contract); misleading example.

### E. Sessions, notes, document map, repository hygiene
1. Finding A.1 (unregistered sessions).
2. Session notes missing template headings: `2026-08-11-architecture-2/3`,
   `2026-08-11-documentation-1` (Open questions, References); `2026-08-11-implementation-1`
   (Decisions, Open questions); `2026-08-18-architecture-1`, `-4` (Scope boundaries, Open questions),
   `-6` (Scope boundaries); `2026-08-18-implementation-1/2/3` (Open questions).
3. `docs/architecture/notes/template.md` uses `## <title>` while all three notes use an H1 title.
4. `CLAUDE.md` is not in the document map (`docs/rules/documentation-rules.md` §1) and carries rule
   content and an architecture summary that duplicate `docs/rules/*` and the overview (§3 one fact in
   one place, §4 entrypoints stay thin). Either add it to the map as an entrypoint with a stated
   exception, or thin it to routing.
5. `.github/copilot-instructions.md` routing drifted from `AGENTS.md`: it lacks `docs/adr/README.md`
   under architecture and the `docs/architecture/overview.md` line.
6. Merged branches not deleted (git-workflow "delete the branch after it is merged"): local
   `docs/architecture-overview-sync`, `feature/adr_006-data-flow-between-nodes`,
   `feature/adr_007-cli-contract-and-session-lifecycle-for-v1`,
   `feature/adr_011-artifact-addressing-and-export`, `feature/adr_012-workflow-input-parameters`;
   remote `origin/feature/adr_006-data-flow-between-nodes`.
7. No files outside the document map in `docs/`; no ad hoc reports; no TODO/TBD/FIXME markers in
   docs or README; all session file names valid; the single `interrupted` session
   (`2026-08-09-implementation-1`) was picked up by `2026-08-09-implementation-2`; notes registry
   complete; all three registries consistent with ADR statuses (all Accepted, no active branches).

## Decisions
1. Nothing is fixed in this session; the findings are the deliverable. Fixes are done by the user in
   follow-up sessions, grouped as they see fit.
2. Finding A.2 is two items: a README correction (documentation) and a `copy_file` behaviour defect
   (implementation, own `fix/` branch, after the release unless the user decides otherwise).

## Open questions
1. Are frozen ADR texts corrected for stale cross-reference labels (D.1) or left as history?
2. Is `CLAUDE.md` added to the document map or thinned to routing (E.4)?
3. Which finding classes deserve a preventive rule: registry completeness check before merge (A.1),
   template-heading completeness for session notes (E.2), overview sync when a signature or a state
   field changes (B.1, B.6), README example must state its preconditions (A.2)?
   Resolved by `2026-08-19-documentation-4_handoff.md`: one rule only (overview sync, added to the
   ADR freeze gate). A.1 and E.2 are left under observation without a rule or a test; A.2 is a code
   defect, not a rule class.

## Next steps
1. Fix A.1 and A.2 (documentation part) before the tag.
2. Apply the B, C, D, E corrections the user selects, in one or more `docs/` sessions.
3. Delete the merged branches (E.6).
4. Merge `development` into `main`, tag `v0.1.0`, push (phase 1 gate item 4).
5. Open a `fix/` session for `copy_file` with a non-existent target directory (A.2 code part).
6. Derive preventive rules from the recorded finding classes (open question 3).

## References
- Branch: `docs/phase1-release-audit`
- Phase 1 completion gate: `docs/sessions/2026-08-18-architecture-5_handoff.md`
- Documents audited: `docs/architecture/overview.md`, `README.md`, `docs/adr/*`,
  `docs/sessions/README.md`, `docs/architecture/notes/README.md`, `docs/rules/*`,
  `docs/processes/git-workflow.md`, `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`
