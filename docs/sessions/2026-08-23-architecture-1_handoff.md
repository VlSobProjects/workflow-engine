# Session note: 2026-08-23 architecture 1

## Type
`architecture`

## Goal
State the purpose of the project in one document, measure the architecture and the open work
against it, and decide for every gap whether it is an ADR, a fix, or component work under an
existing ADR.

## Completion criteria
- `docs/architecture/purpose.md` exists with the agreed text, the document map admits it, and the
  ADR discussion rules require reading it at the start of every architecture session.
- Every gap between the purpose and the architecture is listed below with a decision: ADR, fix,
  component work under a named ADR, or deferred with its trigger.
- The open notes are triaged against the purpose; each is acted on, deferred with a reason, or
  dropped.
- The next sessions are ordered.

## Scope boundaries
- No code, no tests, no examples. Documentation only.
- No ADR is opened or moved to Implementing in this session; the decisions name the ADRs to open.
- The code debts found by the code reading are listed, not fixed.

## Status
`completed` — questions 1 and 5 were decided on 2026-08-23; the session was interrupted while
questions 2, 3, 4 and 6 waited for the `documentation` session of §5 and for the first scenarios,
and was resumed and completed on 2026-08-24 with all of them decided.

## Result
- The twelve gaps of §2 are decided in its table: ADR 014 returns to a narrow Draft and is
  decoupled from ADR 019 (G1, G2), with three shared-mechanism guards so the two instruction
  channels cannot drift; G3 and G8 are covered; G4–G6 are measured by the exit scenario; G7, G11
  and G12 are deferred with named triggers; G9 narrows ADR 019; G10 is a `fix/` session.
- §3, §4 and §6 are settled below; the roadmap steps 5–11 were rewritten to the §6 order.
- The class 2 exit-scenario document moves ahead of the ADR 014 Draft edit, so that its
  `Consumer` section names an existing scenario (rule 11).

## Decisions

### 1. The purpose (question 1, settled)
The text of `docs/architecture/purpose.md` was discussed and accepted; the session writes it. Its
points, as they bind what follows:
- The engine runs a complex technical task as a graph of precisely specified subtasks; functions
  do the deterministic work, models do the judgment, each step by the smallest model that can do
  it; the next node is chosen at run time from the data and is not known in advance.
- The limit of what a model step sees is enforced by the engine, not by the model's discipline;
  the checks at a boundary are code, never a model.
- A situation the author did not foresee is a foreseen exit: a handover to a human carrying the
  evidence. The engine never invents a step.
- A prompt handed to an agent is not automation: somebody watches it. Many steps need no model;
  a pipeline of checks answers before a model is called.
- The engine is a process the caller walks from outside; whoever answers a step answers through
  one contract.
- Boundaries: no planning, no agent framework, no scheduler, no UI; parallel nodes outside the
  current scope (concurrency inside a function first; fork/join only on a serious external
  request); several workflows are several processes, the engine only protects a session from
  concurrent access.
- Done means: a fetch → aggregate → decide → branch → hand over scenario runs end to end on
  prepared data with a local model, its path determined by the data and explained by the
  journal, and an author who knows the domain but not the engine writes it from the
  documentation alone.
- Origin: load-testing analysis. The live check against a real system under test (a Spring Boot
  application the owner already has, a cluster, a metrics store) is the publication gate, not
  the phase 2 exit; it is not started before the prepared-data scenario passes.

Corrections to the reviewer's first analysis that the discussion produced: the note
`2026-08-19-engine-as-team-process-carrier.md` is a later application, not the purpose; the
support-intake scenario is an interview with one answerer and is not the shape the purpose
measures against, so it is not the phase 2 exit condition.

### 2. Architecture measured against the purpose (question 2, settled at the 2026-08-24 resumption)
Each gap carries the reviewer's proposal; the decision column is filled as the discussion goes.

| # | Gap | Evidence | Proposal | Decision |
| --- | --- | --- | --- | --- |
| G1 | No LLM node. The purpose's central component does not exist. | ADR 014 Draft; no `@register_provider`, no `providers` config in `src/` | ADR 014, returned to a narrower Draft: action + `format` parsing, provider registry, `fake` adapter, `providers` config, `llm_called` event, error classes. Cut until a scenario asks: `pre_functions`/`post_functions`, `prompt_ref` as a generic channel, the in-repo reference package. The first real adapter is an OpenAI-compatible local server as an external module (the existing out-of-tree POC). | Decided 2026-08-24 (resumed): the narrow Draft as proposed; the cut items move to Leaves open. Order amended: the class 2 exit-scenario document is written before ADR 014 enters Implementing, so its `Consumer` section (rule 11) has a scenario to name. |
| G2 | Ordering: ADR 019 §2 makes the LLM node consume the rendered question document; ADR 014 §1 makes the prompt template text. Two Drafts contradict on one field. | ADR 019 Consequences "Constrains: ADR 014"; ADR 014 §1 | Decouple. The LLM node's input is a prompt (ADR 016 template text) plus the answer declaration; the question document of ADR 019 is for an answerer outside the run. Edit ADR 019 (Draft) to drop the constraint. Order: ADR 014 first, because the exit scenario needs it and needs no external answerer; ADR 019 second. | Decided 2026-08-24: decoupled; ADR 019 is edited in place (the constraint and the §2 prompt paragraph go). Three shared mechanisms are recorded in both Drafts so the channels cannot drift: one answer-shape generator from the answer declaration and the codec value forms, consumed by the ADR 019 protocol section and, when a scenario asks, by the ADR 014 prompt; one template-file loader, `prompt_ref` its first instance; `node.` as a prefix of the template-text contract, resolved on any node, not an `ask` property. |
| G3 | Model tiering per step and context limited to the declared inputs. | ADR 014 §1 `provider`/`model` per node; ADR 016 references | Already covered by ADR 014 as drafted and by ADR 016. No work beyond G1. | Decided 2026-08-24: covered; `provider`/`model` per node and the single-pass interpolation stay in the narrow Draft, no separate work. |
| G4 | Nothing checks that a structured answer has the shape the step declared: `type: dict` accepts any dictionary. | `support-intake` note gap 4; ADR-0083 note | A guard over answer keys (component work under ADR 002; the guard name is the error code). Declaring the shape in `answer` is an ADR 013 change and is not taken until a scenario shows the guard is not enough. | Decided 2026-08-24: the guard, as component work under ADR 002, built when a scenario asks for it (support-intake gap 4, the exit scenario); the escalation trigger to a shape declaration in `answer` is recorded: the published shape description (the shared generator of G2) and the check must feed from one source. |
| G5 | The function inventory is filesystem sediment: 21 of 30 functions are file work; no function creates or sets a dictionary parameter; no generic fetch/parse/aggregate step. | code audit; `support-intake` gap 1 | Core gets only generic bus work: `init_dict_param`, `set_dict_item` (component work under ADR 006). Scenario-specific fetching and parsing ship as an external module beside the scenario in `examples/`, the way the purpose keeps vendor and domain code outside the core. The 15 file-info functions leave the core in a later `refactor/` session. | Decided 2026-08-24: the dict functions are built when the exit-scenario document names its aggregate step, not ahead of it; scenario fetch/parse ships as an external module beside the scenario; the eviction of the file functions is out of phase 2 (the phase is additive) and is re-decided at the phase exit or the publication gate. |
| G6 | One output shape, a table in six syntaxes; a handover is a structured document; an artifact name cannot carry a run value; template text is confined to the ten `ask` fields. | `support-intake` gaps 2 and 3; `template=True` appears only in `action_ask.py` | One ADR: template text outside `ask` (function parameters declared template text in their metadata) and document artifacts — a JSON artifact of author-defined shape and a text artifact rendered from template text. Opened when the exit scenario needs its handover, not before; it amends the scope of ADR 016 and ADR 011. | Decided 2026-08-24: deferred to the exit scenario's handover; the outcome of the hand-built scenario must either open the ADR or record why the existing means sufficed; the opening session checks rule 3 — whether template text outside `ask` and document artifacts are one decision or two. |
| G7 | The unforeseen exit. A node that fails with no matching transition fails the run; every handover route has to be written per node. | ADR 002 transition semantics; overview "A node" | Defer. The scenario writes its failure transitions explicitly; if that proves verbose, a workflow-level default failure route is its own ADR amending ADR 002. Retry/backoff by error class (recovery note (b)) waits for ADR 014's error classes, as already decided. | Decided 2026-08-24: deferred; the trigger is the verbosity of the explicit failure transitions in the hand-written exit scenario. |
| G8 | A run explained and repeated from the journal. | ADR 018 journal and guard traces; ADR 014 §4 prompt/reply artifacts | Covered by ADR 018 and ADR 014 §4 as drafted; a replay mode is not needed for "done" and is deferred. | Decided 2026-08-24: covered; §4 audit stays in the narrow Draft (the purpose requires every model answer recorded), replay deferred with no trigger. |
| G9 | An external answerer cannot compose an answer from the published block alone. | ADR 019 Draft, context | ADR 019 stays, after ADR 014, narrowed: typed document, `md` and `json` renderers, the protocol published inside, `node.` references, one publishing command. §7 `instruction_file` and §9 audit copy are cut until asked for. The codec-name question of `adr012-deferred-questions` §2 is settled inside it, since both touch `CodecMetadata`. | Decided 2026-08-24: narrowed as proposed, with four clarifications: the `text` renderer is cut too, `md` serving a human who takes over, and `simple_render.py` is replaced by the `md` renderer; the file loader keeps `prompt_ref` as its only instance, `instruction_file` recorded in Leaves open as its second; the counter guard demotes from `Depends on` to Leaves open; `Consumer` names `repository-interview`. |
| G10 | `state.json` is overwritten in place; nothing protects a session from two processes. | recovery note (c); `storage/` has no `os.replace` | One `fix/` session without an ADR: atomic write and a session lock or concurrent-access check. Already planned since 2026-08-19; still undone. | Decided 2026-08-24: a `fix/` session without an ADR — the lock implements a promise `purpose.md` already states; independent of the ADR chain, to be taken without further delay. |
| G11 | "An author who knows the domain writes it from the documentation alone" has no authoring surface: no command validates a definition without running it and no `describe-workflow`. | `adr012-deferred-questions` §3 | Defer until the exit scenario has been written by hand; then one ADR for the authoring surfaces (validate, describe) as additive commands under the ADR 007 contract. | Decided 2026-08-24: deferred; the trigger is the hand-building of the exit scenario, which gives the lower bound of the authoring need; the final measure is the phase done-condition. |
| G12 | No licence, no version flag, no delivery channel. | `installation-and-distribution` note; `pyproject.toml` | Publication gate, not phase 2. `--version` is a chore. | Decided 2026-08-24: publication gate; `--version` is a chore outside architecture work. |

### 3. State of the development and the diagnosis of the wrong path (question 3, settled)
Facts established by the reading, for the discussion to weigh:
- ADR 013 §6 ("the engine has no way to know who is reading, so it declares nothing about the
  intended audience") was decided on 2026-08-19 and diagnosed as wrong on 2026-08-22. Between the
  two: 28 sessions and four accepted ADRs (015–018), all on the `ask` node. The first reader-side
  signal appeared one day after the decision (`2026-08-20-investigation-1`: a re-presented
  question tells the answerer nothing; a `Path` published as `pathlib._local.Path`) and was
  dispersed into three ADRs about the node, because that session was scoped to computation
  inside the node and no session owned "what the answerer sees" until `2026-08-21-investigation-2`.
- Root cause, from the ADR text: decided before a consumer existed (ADR 013: "exercised by engine
  tests only", "no open question remains that only code could answer"), and written from the
  engine's point of view (§6 argues what the engine knows, alternative E what it can enforce,
  alternative G what it versions; none asks what the reader needs). Without a written purpose no
  ADR had "an answerer can act from the published surface alone" as an acceptance criterion.
- The same conditions hold for ADR 014 today: settled to "ready to enter Implementing" on
  2026-08-21 on paper, against a POC outside the repository, with no consumer in the tree, carrying
  fourteen concerns of which its own Costs list names eight, and `pre_functions`/`post_functions`
  added "after a follow-up discussion" without a scenario.
- Code: 458 tests pass, `ruff` clean. The published boundary of the interactive exchange is held
  by one function (`answers.question_block` building an untyped dictionary) and one journal check
  in `use_cases._with_pending_question`; the enforcement is the CLI contract tests. This confirms
  the ADR 019 diagnosis at the code level.
- Reviewer's position: the wrong path is a process defect, not a design defect, and the repair is
  the purpose document plus the consumer rule of §5 below; no code is rolled back.

Decision (2026-08-24): the reviewer's position is confirmed. The same code that carried the defect
now carries the `repository-interview` scenario, so nothing is rolled back; ADR 019 repairs the
published surface forward as a regular supersede; the process repair — `purpose.md`, the consumer
rule, scenarios as documents — is in force, and the G1–G12 pass of this session is its first
application: ADR 014 was caught on the same pattern before implementation instead of after.

### 4. Notes triage against the purpose (question 4, settled)
Eleven notes open, four promoted, none dropped; about 14,700 words open; the batch of 2026-08-19
(seven notes) has resolved none. Reviewer's proposal per note:

| Note | Proposal |
| --- | --- |
| `2026-08-21-support-intake-use-case` | Keep open as the scenario of the interactive node; not the phase 2 exit. Its gaps 1–4 are G4–G6 above. |
| `2026-08-21-agent-instruction-and-skill` | Act after ADR 019 (its gaps 2 and 3 are what ADR 019 closes); Skill deferred to the publication gate. |
| `2026-08-19-adr0083-scenarios-coverage` | Close: `promoted → ADR 015, 016, 017`; its two residuals (an in-graph budget checkpoint; a guard reading a pending write) move to one short note or are dropped. |
| `2026-08-19-interactive-exchange-publishing-boundary` | Stale: §1 and §3 are answered by ADR 019 §2 but `Affected` does not name ADR 019. Mark promoted in part; §2 (identity) deferred. |
| `2026-08-18-adr012-deferred-questions` | §2 (codec names) settled inside ADR 019 (G9); §1, §3 (G11), §4 deferred. |
| `2026-08-18-recovery-and-resilience-roadmap` | (c) is G10, do now; (b) after ADR 014; (d)/(e) stay. |
| `2026-08-19-installation-and-distribution` | Publication gate (G12). |
| `2026-08-19-engine-as-team-process-carrier` | Keep as a later application; mark that it is not the purpose. |
| `2026-08-19-node-save-as-redundancy` | Candidate to drop unless a scenario asks for author-named outputs. |
| `2026-08-19-hard-node-cap-scoping`, `2026-08-19-entry-point-discovery` | Deferred, untouched. |

Proposed rule for the channel: a registry row is one sentence; a note that is amended a third time
is closed or split.

Decisions (2026-08-24): the table's proposals stand, with the three open choices resolved:

- `adr0083-scenarios-coverage` closes as `promoted → ADR 015, 016, 017` with no successor note:
  both residuals — the in-graph budget checkpoint as an ADR 010 change, and a guard over pending
  writes when a second flow asks — stay recorded inside the closed note, findable through the
  registry.
- `node-save-as-redundancy` is dropped: no consumer asks for it, and it is re-raised by the
  output-family ADR of G6 or by a scenario that needs author-named outputs.
- `support-intake` stays open; its reformatting into a class 2 scenario is its own `documentation`
  session, scheduled beside the ADR 019 narrowing, whose second consumer it is.

Executing the status edits is the notes-maintenance session (roadmap step 11), now mechanical. That
session also checks the proposed third-amendment rule and adds it to the notes rules if absent.

### 5. The documentation system (question 5, decided)
- What works: the registries hold the truth after an audit, not during the work; the freeze gate
  with the overview synchronization catches drift; the session format keeps scope narrow.
- Measured: 136,000 words of documentation against 33,000 words of code; 99 session notes in
  about 25 days; the session and note registry rows are paragraphs of 100–150 words, so the
  indexes are read, not scanned. Diagnosis: text is produced faster than decisions are checked
  against a consumer, which is the mechanism behind §3. The volume is the symptom; the repair
  puts the consumer into the gate and makes the indexes scannable.
- The uncommitted work of session `2026-08-22-architecture-1` (ADR 019 and registry rows) was
  found on `development` and is committed before this session's changes.

Decisions, to be carried out by one `documentation` session (§6 step 2):

1. **Consumer rule.** Not in the wording first proposed (blocking the exit from Draft would
   deadlock a surface that exists only after Implementing). Instead: the ADR template gains a
   mandatory `Consumer` section, filled from Draft, naming who acts on the decision — a human, an
   external program, or a model — and the scenario it serves; the freeze gate in
   `docs/adr/process.md` requires evidence that the consumer can act from the surface, supplied
   by a scenario of class 2 or 4 below. A synthetic e2e test is not evidence: ADR 013 was
   "exercised by engine tests only", and that is the defect being repaired. A Draft may not
   constrain another Draft; a constraint is written only against an accepted ADR (`adr-rules.md`
   §5).
2. **Scenarios become a kind of document**, `docs/architecture/scenarios/` with a registry, a row
   in the document map. A scenario has a stable identifier and a fixed header: who answers each
   step, the prepared input data, the expected paths through the data, how it ends, and the live
   list of ADRs it exercises. Scenario and ADR relate many-to-many; the one truth for the
   relation is the list in the scenario, since an accepted ADR cannot be edited. Order of work:
   the scenario is written first; architecture and investigation sessions find the decisions it
   lacks; a new ADR names the scenario in `Consumer` and the scenario adds the ADR to its list in
   the same session. The classes:
   - the class of tasks in `purpose.md` is not a scenario and does not filter work: what a
     future application needs cannot be known now; the purpose measures through `Boundaries` and
     `What counts as done`;
   - class 2, an external task written in full: the first two rows are the interview that
     creates a repository and its documents (the development loop it feeds runs outside the
     workflow; recorded so far only in session notes of another project, to be written from the
     owner's account) and the support-intake interview (note `2026-08-21-support-intake-use-case`,
     reformatted);
   - what was class 3 is renamed: synthetic e2e tests, in `tests/` and in a sandbox through the
     CLI, built to check nodes through a real agent; they have paid for themselves (two
     investigation sessions) but mean little to a human reader and are not scenarios; renaming
     `test_adr0083_scenario.py` and the note `adr0083-scenarios-coverage` goes to the `refactor/`
     session;
   - class 4, the shipped examples: they stay in `examples/` with the same header in the
     walkthrough and one registry row in `scenarios/`; one example with named variants replaces
     several that derive from one another; every named variant is covered by a test or marked as
     not verified.
3. **Roadmap.** `docs/architecture/roadmap.md`, a row in the document map: a table of the steps
   of the current phase and the exit scenario of each phase. The form is fixed (one sentence per
   row, rewritten rather than appended); the content is expected to change, and the session that
   changes it records why. `adr-rules.md` rule 10 reads it after the purpose. A phase is closed
   when its exit scenario passes and every `open` note has been triaged. Phase 1 is closed by
   this session at the commit that brought `purpose.md` into `development`; `main` lags
   `development` by 84 commits and does not define the boundary.
4. **Registries.** A registry row is one sentence; what the row carried moves into the document
   it points to, nothing is lost. `docs/sessions/README.md` lists the current phase; each closed
   phase has its own archive file; files are not moved (62 session notes link to other session
   notes by path). The notes registry is split into four sections — current phase, later
   phases, not triaged, closed — with the `Status` header of the note as the only truth; files
   are not moved (`Affected` links). A note does not declare its phase; the triage in an
   architecture session assigns it. The rewrite of the existing rows is part of the
   `documentation` session. Splitting sessions into one directory per type was proposed and
   rejected: type is a weak axis for finding (one ADR crosses investigation, architecture and
   implementation), the type is already in the file name and the row, and the move would relink
   62 files for five registries.

Documents the `documentation` session changes: `docs/rules/adr-rules.md` (§5, §10),
`docs/adr/process.md` (freeze gate), `docs/adr/template.md` (`Consumer`),
`docs/rules/documentation-rules.md` (map rows for `scenarios/` and `roadmap.md`),
`docs/architecture/notes/README.md` (registry sections, triage at phase close),
`docs/sessions/README.md` (phase registry and archive), new `docs/architecture/roadmap.md` and
`docs/architecture/scenarios/README.md`; then the session that writes the first class 2 scenario.

### 6. Priorities (question 6, settled)
Reviewer's proposed order, to be revised by the decisions on G1–G12:
1. Commit the 2026-08-22 session; write `purpose.md`, the map row and the reading rule (done in
   this session).
2. The `documentation` session of §5: consumer rule and `Consumer` section, scenarios as a kind of
   document, `roadmap.md`, the registries rewritten to one-sentence rows and split by phase. Then
   the session that writes the first class 2 scenario (interview → repository → documents).
3. ADR 014 back to a narrow Draft, its §1 decoupled from ADR 019; the first adapter as an external
   module; then Implementing (G1, G2).
4. The `fix/` session for the atomic state write and the session lock (G10).
5. Write the exit scenario by hand on prepared data with the components that exist, to measure
   G4–G6 before opening the output-family ADR.
6. ADR 019 narrowed, after ADR 014 (G9).
7. One `refactor/` session for the code debts of the audit: dead code (`def_errors`,
   `SubmitStatus`, `SubmitResult`, `PresentResponse.submit`/`expected_input`,
   `renderers/simple_render.py`, empty `runtime/` and `parsers/` packages), misspelled identifiers
   (`storage_fatcory`, `_get_commend`, `_factory_sate_stub`, `intend`), the duplicated tail of
   `run_workflow`/`resume_workflow`, `from_state`/`from_state_full`, the five `parameter_from_dict`
   variants, the 163-line `_start_engine`; after ADR 019 so as not to cross `PresentResponse`.
8. Notes maintenance session (§4).
Not now: retry/backoff, authoring surfaces (G11), distribution, Skill, entry-point discovery,
the team-process carrier, the counter guard of ADR 019 alternative H, parallel nodes.

Decided 2026-08-24: the order stands with one change, written into `docs/architecture/roadmap.md`
as steps 5–11: the class 2 exit-scenario document is written before the ADR 014 Draft edit, because
rule 11 names the consumer from Draft on and a scenario is written before the decisions it needs.
The `fix/` session of G10 is independent of the ADR chain and is taken at any pause. The "not now"
list stands unchanged.

## Open questions
None.

## Next steps
1. Roadmap step 5: a `documentation` session writes the class 2 exit-scenario document.
2. Roadmap step 6: an `architecture` session edits the two Drafts — ADR 014 to the narrow Draft
   (G1), ADR 019 decoupled with the three guards (G2) — fills their `Consumer` sections and moves
   ADR 014 into Implementing.
3. The `fix/` session of G10, taken at any pause.

## References
- Branch: `development` — documentation only.
- Documents changed: `docs/architecture/purpose.md` (new, 2026-08-23),
  `docs/rules/documentation-rules.md` (map row), `docs/rules/adr-rules.md` (reading rule),
  `docs/architecture/roadmap.md` (steps 5–11 rewritten at the resumption), the session registry.
  The notes status edits themselves go to the maintenance session (§4).
- Related ADRs: ADR 014 (Draft), ADR 019 (Draft), ADR 013, ADR 016, ADR 002, ADR 011.
- Code audit of this date: 458 tests pass, `ruff check` clean; the code debts it listed are
  recorded for a later `refactor/` session and not decided here.
