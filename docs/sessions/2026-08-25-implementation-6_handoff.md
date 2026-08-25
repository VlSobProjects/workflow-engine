# Session 2026-08-25-implementation-6

## Type
implementation

## Goal
Deliver roadmap step 10 in its revised form: the plan half of a new class 4 example,
`reorganize-folder` — an audit of a folder tree that ends in a reorganization plan as text and as
a dictionary — taking the four measurements: the answer-keys guard (G4), the dictionary half that
remains of G5, the failure-route verbosity (G7) and whether inline template text carries a
paragraph prompt.

## Completion criteria
- Roadmap row 10 rewritten from the triage slice to the class 4 measurement build, with the why
  recorded here: none of the four measurements requires the triage domain — G4 and the G5
  remainder need any dict-assembling flow, G7 needs node count, prompt location needs a
  paragraph-length instruction — while a slice would still be rewritten at step 12 once the
  generated data exists, and a class 2 document would grow the scenario registry for a one-off
  measurement. The build is a new example rather than a variant of `folder-inventory-to-csv`
  because its deliverable — a reorganization plan, not a CSV inventory — is another identity, not
  a derived variant; and it is the plan half of a two-stage example so the audit flow is not
  thrown away when the applying half is built.
- Duplicate detection is deterministic: files are hashed in code and grouped by hash into a
  dictionary — the consumer that makes append-under-key a named G5 need — and the model only
  recommends what to do with the groups, never finds them.
- The G5 dictionary functions (`init_dict_param`, `set_dict_item`, `append_to_dict_key`) ship as
  component work under ADR 006 with tests.
- The G4 answer-keys guard ships as component work under ADR 002 with tests, or the reason it
  cannot stay a guard is recorded with the escalation evidence the 2026-08-23 audit asked for; the
  `moves` dictionary, whose keys are paths no closed list can check, is recorded as the boundary
  of the guard approach either way.
- The example ships: the `reorganize-folder` template, its walkthrough, the scenario registry
  row, a test through the `fake` adapter.
- The four measurements are recorded in this note as facts with the evidence that produced them.
- `uv run pytest` and `uv run ruff check .` run clean from the command line.

## Scope boundaries
- No ADR is opened: the components are the work ADR 002 and ADR 006 already sanction, gated on a
  scenario asking — this variant is the asking. If G4 escalates to a shape declaration in
  `answer`, the escalation is recorded, not decided.
- The `load-test-triage` scenario, its data generation and the drift-B protocol stay untouched
  (roadmap steps 11–12).
- ADR 019 and everything of phase 3 stays untouched.
- G7 gets a reading here, not its trigger: the recorded trigger for a workflow-level default
  failure route remains the hand-written exit scenario.
- The applying half of the example — the `ask` confirmation, the deterministic plan validation,
  the moves and deletions — is deferred to its own session; where it sits on the roadmap is an
  open question raised at the merge, and no preliminary document is written for it: the walkthrough
  and this note are its record.

## Status
`completed`

## Result
- The dictionary family shipped in `modify_param_functions.py`: `init_dict_param`,
  `set_dict_item`, `append_to_dict_key` and `filter_dict_by_value_size`, all riding the
  `DICT_UPDATE` write mode the engine already had, keys rendered as text by the one rule. The
  fourth function was not in the confirmed list and is flagged as such: grouping by hash is only
  useful if code can extract the groups that matter, and the alternative was handing that
  filtering to the model.
- The G4 guard shipped as the registered validator `is_answer_keys_valid`, used through the
  existing `FunctionGuard` — no new guard class, no factory change. It reads the pending write of
  the node being routed, the surface `echo_answer` already reads.
- The `reorganize-folder` example shipped: 17 nodes, the plan template, the walkthrough, rows in
  `examples/README.md`, the root `README.md` and the scenario registry, and six end-to-end tests
  through the `fake` adapter covering the plan path, the shared hash, the call count, the re-ask
  on invented keys, `max_attempts_exceeded` and the refusal of a file-less tree before any model
  call.
- 25 unit tests for the dictionary family and the guard in `test_dict_param_functions.py`.

## The four measurements

- **G4, the answer-keys guard.** A registered validator over the pending write suffices for a
  closed key list: `counts_by_category` checked against `param.categories`, an invented key
  re-asks the decision bounded by `max_attempts`, exhaustion fails under `max_attempts_exceeded`.
  The boundary of the approach showed exactly where predicted: the `moves` dictionary, whose keys
  are paths, cannot be checked by any key list — its check is deterministic validation against the
  file system, which is the applying half's first node. The escalation to a shape declaration in
  `answer` (the 2026-08-23 audit's trigger) was not needed for this scenario.
- **G5, the dictionary half.** `DICT_UPDATE` carried everything; no engine change was needed, only
  functions. The measurement the audit wanted is now concrete: create, set-one-key,
  append-under-key and filter-by-group-size are the four operations a dict-assembling flow
  actually used. What did not come up: deleting a key, merging two dictionaries.
- **G7, failure-route verbosity.** 17 nodes carry 36 transitions, of which 13 are failure routes
  and 3 retry routes — a third of the definition is failure plumbing, and most of it is the same
  `{no_error → next, fail code}` pair repeated. The reading supports the audit's suspicion, but
  the trigger stays the hand-written exit scenario as decided.
- **Prompt location.** The decision prompt is ~1750 characters of multi-paragraph instruction
  inline in a JSON string. It works — ADR 016 interpolation carries it — but it is written and
  reviewed as one escaped line, which is exactly the authoring pain `prompt_ref` (deferred by the
  narrowed ADR 014) would remove. The reading: inline text suffices mechanically and hurts
  editorially; the triage prompts (step 12) decide whether that pain justifies the channel.

## Decisions
1. **The G4 check is a validator function, not a guard class.** A new guard class would change the
   factory and the config surface for something `FunctionGuard` already carries; the validator
   registry is the sanctioned extension point of ADR 002, and the guard name in `validators` stays
   the error code.
2. **A string answer of an `llm` node cannot be checked before it lands without an extra node.**
   `CLASSIFY`'s `file_category` goes unchecked per file: ADR 015's post-function is `ask`-only, a
   guard reads output text and the raw JSON reply is not the value. The invented category is
   caught later by the decision's checked counts. Recorded as a measurement observation feeding
   the triage build, not solved here.
3. **A per-file re-ask bound has no mechanism.** `max_attempts` bounds re-asks of one visit and
   `max_visits` counts across the whole run, so a repair loop per file cannot be bounded without
   flow data; the example therefore does not re-ask on a bad category. Known limitation, recorded.
4. **`set_dict_item` refuses a non-dictionary itself** instead of letting the write layer answer
   `invalid_write_mode`: the family reports `param_type_mismatch` uniformly.
5. **The table writes before the decision**, so an empty tree fails under `nothing_to_plan` before
   any model call — the pre-check shape of the triage scenario, demonstrated in a class 4 example.

## Open questions
- Where the applying half (`apply` variant: `ask` confirmation, deterministic move validation, the
  moves and deletions) sits on the roadmap — raised at the merge, phase 2 does not need it.
- Whether the dictionary family eventually needs delete-key and merge, which nothing asked for.

## Next steps
1. Merge; add the session registry row and reconcile the example registries on `development`.
2. Decide the roadmap placement of the `apply` variant at the merge conversation.
3. Roadmap step 11: data generators and the drift-B protocol.

## References
- Branch: `feature/reorganize-folder-example`
- ADRs: ADR 002 (guard component), ADR 006 (dictionary functions), ADR 014 (`llm` node, `fake`
  adapter), ADR 020 (report writer)
- Documents: `docs/architecture/roadmap.md` (row 10), `examples/folder-inventory-to-csv.md`,
  `docs/architecture/scenarios/README.md`, `docs/architecture/scenarios/load-test-triage.md`
  (consumer sentence re-pointed at step 12)
