# Session 2026-08-25-architecture-2

## Type
architecture

## Goal
Recompose the phases of the roadmap around the two-drifts seam and rewrite step 10, triaging the
three notes of 2026-08-25 in the same pass; no ADR is opened or edited.

## Completion criteria
- The phases table states a narrowed phase 2, a new phase 3 for assisted authoring, and the
  unchanged publication gate, each with a one-sentence exit.
- Phase 2 step 10 is replaced by steps that keep its measurements and add the data generators and
  the drift-B experiment protocol.
- The G5 remainder is verified against the code, not against the audit table.
- `purpose.md` "What counts as done" no longer contradicts the split.
- The three 2026-08-25 notes are moved out of "Not triaged" with a phase each.
- The question of a roadmap row for the version scheme is answered.

## Scope boundaries
- ADR 019 is not edited; its content and narrowing wait for phase 3.
- No refactoring, no data generation work itself, no experiment protocol content — only their
  place on the map.
- The stale rows of the older notes stay for roadmap step 14 (the 2026-08-23 triage execution).
- The pre-existing staleness of `load-test-triage` open decisions 1 and 4 (ADR 014 and ADR 020 are
  now Accepted, the text still calls them pending) is noted, not fixed: the list is revisited by
  the hand-build steps.

## Status
`completed`

## Result
- `roadmap.md`: phase 2 narrowed to the engine for hand-written workflows — exit is the
  `load-test-triage` run on generated data, hand-written by an author deliberately working from the
  operator documentation alone, measured against the `fake`-adapter reference by numbers declared
  before the runs. Phase 3 added: assisted authoring, exit is the blind-agent drift-A experiment.
  Publication row unchanged. Old steps 10–13 rewritten as 10–14; the ADR 019 / `support-intake`
  step left the phase 2 list and is named in the phase 3 paragraph.
- `purpose.md`: the done condition keeps both halves but splits them across two phase gates; the
  authoring half is restated mechanism-neutrally, with documentation as the floor and assisted
  authoring as the proof.
- Notes registry: `two-drifts-and-their-measurement` → current phase;
  `role-separation-answerer-and-operator` → later phases (phase 3);
  `version-numbering-and-architecture-eras` → later phases (publication).
- Scenario documents: the consumer paragraphs of `load-test-triage` and `workflow-authoring`
  re-pointed at the split; `load-test-triage` open decision 2 rewritten to the verified G5
  remainder.

## Decisions
1. **The phase split follows the two-drifts seam.** Drift B (one definition across providers) is
   phase 2; drift A (one brief across authoring agents) is phase 3. Alternatives rejected: keeping
   one phase 2 leaves the gate hanging on the least-decided half (ADR 019 Draft, G11 undecided,
   the role model a note); pushing authoring into publication recreates the same bundling one
   phase later while the live-run gate needs only the phase 2 artifact.
2. **Phase 3 is kept finite by construction, because the risk it inherits is real** — its opening
   surface (eight open decisions in `workflow-authoring`, ADR 019, G11, the role model) is larger
   than phase 2's was. Three bounds are written into the phase paragraph: the gate is a runnable
   experiment, not "authoring is solved" — at least one blind agent's definition validates and
   runs its expected path, the cross-vendor divergence is measurement, not gate; enforcement of
   the answerer/operator split stays outside the phase (narrow entry plus kept transcript is the
   blindness evidence, per the role-separation note); the experiment targets one triage-class
   workflow through the universal cycle, not "any workflow".
3. **Step 10 splits into three steps, not a replacement.** A wholesale swap to generators and
   protocol would lose the measurements step 10 existed for; the reduced slice keeps them cheap.
   The slice is a hand-built cut of `load-test-triage` on a toy dataset, not a new scenario
   document — the scenario registry does not grow for a one-off measurement.
4. **G5 remainder verified by code.** Shipped since the ADR 014 variants: `split_text_to_deque`,
   `append_to_param`, `collect_answer`, `init_list_param`, `init_deque_param`,
   `set_param_from_deque`, `read_text_file`. Remaining: the dictionary half — nothing creates or
   sets a dictionary parameter — and gap G4 (the answer-keys guard) is untouched. Step 10 measures
   exactly these.
5. **Cloud providers are measurement, not gate.** The phase 2 gate holds on the reference run and
   the local model; runs against cloud vendors belong to the drift-B protocol as extended
   measurement, so the phase cannot be blocked by external keys, cost or availability.
6. **Assisted authoring is the stronger proof of the authoring claim, not a reading of
   "documentation alone".** It fulfils the spirit — authoring must not require engine expertise —
   through a stronger mechanism (the engine carries the engine knowledge), while the letter
   proved only documentation quality. `purpose.md` now states the claim mechanism-neutrally;
   leaving it untouched was rejected because rule 10 argues every decision against `purpose.md`,
   and a gate contradicting its letter would be re-litigated every session.
7. **No roadmap row for the version scheme.** The roadmap lists steps only for the current phase;
   the publication exit row already names the version flag, which anchors the note. The scheme is
   decided in the session that opens the publication step list.
8. **Only the current phase carries a step list** — stated in the roadmap preamble, so phase 3's
   surface is planned when the phase opens, not speculatively now.

## Open questions
- Where the drift-B results live: a scenario body is not a lab notebook and
  `documentation-rules.md` admits no report document — the protocol step (roadmap 11) will force
  this documentation decision.
- The `two-drifts` note is triaged to the current phase for its B half; at phase close its A half
  is expected to be recorded as encoded in the phase 3 exit row, closing or splitting the note.
- Whether the phase 3 gate's "at least one agent succeeds" clause is the right floor, or the
  human-direct variant should serve as the fallback proof when every vendor agent fails.

## Next steps
1. Roadmap step 10: hand-build the reduced slice on a toy dataset and take the G4, G5-remainder,
   G7 and prompt-location measurements.
2. Roadmap step 11: data generators and the drift-B protocol, deciding where the declared numbers
   and the results live.
3. On merge: add this session's registry row and reconcile the notes-registry moves on
   `development`.

## References
- Branch: `docs/phase-composition`
- Changed: `docs/architecture/roadmap.md`, `docs/architecture/purpose.md`,
  `docs/architecture/notes/README.md`, `docs/architecture/scenarios/load-test-triage.md`,
  `docs/architecture/scenarios/workflow-authoring.md`
- ADRs: none opened or edited; ADR 014, ADR 019, ADR 020, ADR 021 argued from
- Notes: `2026-08-25-role-separation-answerer-and-operator`,
  `2026-08-25-two-drifts-and-their-measurement`,
  `2026-08-25-version-numbering-and-architecture-eras`
