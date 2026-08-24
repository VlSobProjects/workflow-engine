# The first use case that is a reason to adopt the engine, and what it cannot express yet

- **Date:** 2026-08-21
- **Trigger:** discussion in session `2026-08-21-investigation-1`, while planning a generic
  interactive template for `examples/`. The observation that opened it: the three shipped templates
  scan a folder, copy a tree and approve a copy. They demonstrate the engine; none of them is a
  reason to adopt it. The question was which scenario is — and the answer proposed was an agent
  taking a technical-support call for an internet provider to the point where a human operator can
  act on it.
- **Status:** open
- **Affected:** ADR 020 (gap 3 decided — the text write and the grouped document ship; gap 2
  deferred with this note's reformatting as its trigger), ADR 005 (registered components — every
  gap below is a missing component or a missing decision about one), ADR 011 (artifact addressing
  and export — the output shapes), ADR 013
  (interactive exchange — the flow is one interview), ADR 014 (Draft; the answerer that judges),
  ADR 016 (interpolation scope — a composed artifact name is outside it),
  `2026-08-19-adr0083-scenarios-coverage.md` (the same genre of measurement, for an external
  repository's scenarios)

## Why this scenario and not another

The scenarios the engine has been measured against so far were chosen because they were cheap to run:
a folder walk, a file copy, and the ADR-0083 questionnaire flow borrowed from an external repository.
They proved that the machinery works. None of them answers the question a reader of `README.md`
actually has, which is why a graph of guarded nodes with a persisted state is worth more than a
script.

A support intake answers it. The work is a *process a company owns*: it has a fixed opening, a
mandatory identification step with a bounded number of retries, a diagnosis that follows a checklist
the company wrote, a bounded amount of digging when the diagnosis is inconclusive, and a handover
whose shape the receiving side depends on. It is answered by an agent, it can be interrupted and
resumed, it must never hand over something incomplete without saying so, and every step of it has to
be auditable afterwards. That is the whole argument for this engine, in one flow.

This note records the flow and measures it against the components that exist. It does not design the
solution to what is missing.

## The flow as proposed

1. **Load the account record.** A node standing in for a lookup in the provider's own system: given an
   account number, it produces the record as a dictionary parameter. In a shipped example it is an
   emulation; in a real deployment it is a plugin function under ADR 005.
2. **Identify the caller, three attempts.** The account number is asked, and the node checks what it
   bound. If three attempts pass without an identifiable account, the run ends on a `stop` that tells
   the caller how to find their account number — *without* opening a ticket.
3. **Open the ticket.** Once the account is known, a ticket is opened unconditionally. Its number
   becomes part of the name of what the run hands over: `<ticket>_intake_table`, not a fixed name.
4. **Diagnose from what the caller said.** The agent is given the caller's own words and the company's
   checklist, and must return the checklist back with a verdict per item — exactly the declared items,
   nothing invented.
5. **Branch on whether the diagnosis is conclusive.** If one checklist item clearly points at the
   problem, the flow goes straight to the handover. If not, it asks up to two follow-up questions,
   derived from the diagnosis, and accumulates the answers.
6. **Hand over.** The ticket, the account record, the checklist with its verdicts and the follow-up
   pairs go to the operator. When the diagnosis never became conclusive, the handover also carries a
   speculative cause, marked as speculation.

## What the engine has, measured

There are 28 registered functions. 19 of them are filesystem work: all 13 of
`actions/file_info_functions.py`, four of the five in `actions/base_functions.py` (`copy_file`,
`copy_file_to_folder`, `create_folder`, `file_delete`) and two of the six in
`actions/modify_param_functions.py` (`read_folder_items_to_deque`, `enqueue_folder_entries`). The
inventory is the sediment of the two demonstration templates.

What is left for a flow that touches no disk is nine functions: `echo_value`, `echo_answer`,
`collect_answer`, `init_list_param`, `init_deque_param`, `set_param_from_deque`, `append_to_param`,
`dict_list_to_pretty_table` and `copy_artifact`.

There are six guards in `validators/output_function_validators.py`, four of which check a path or a
substring: `is_output_exist_file`, `is_file_exist`, `is_output_contains_str`,
`is_output_exist_folder`, `is_output_number`, `is_collection_size_at_least`.

## What the flow needs and cannot get

1. **A dictionary parameter cannot be created by anything.** `modify_param_functions.py` initializes a
   list (`init_list_param`) and a deque (`init_deque_param`); `append_to_param` extends an existing
   collection. Step 1 — the node that produces the account record — has nothing to build with. A
   dictionary can only enter the bus today as an answered value declared `type: dict`, which makes an
   external lookup impossible to express as anything but a question to a human.

2. **The artifact name cannot carry the ticket number.** `${...}` interpolation is confined by ADR 016
   to fields declared template text, and `template=True` appears in exactly one place in the source:
   the ten presentation fields of the `ask` action (`actions/action_ask.py`). Function parameters take
   a bare `param.<name>` reference that resolves to the whole value, so
   `"artifact_name": "${param.ticket_id}_intake_table"` is not a thing the engine does. Step 3 is
   inexpressible as stated. The ways out are a widening of ADR 016's scope to function parameters, a
   function that composes a name, or an artifact function that takes its name in parts — three
   different decisions with three different blast radii.

3. **There is one output shape and it is a table.** `dict_list_to_pretty_table` renders `html`, `csv`,
   `json`, `latex`, `mediawiki` or plain text (`pretty_table_str` in
   `actions/create_artifact_functions.py`) — and every one of those is the same table in a different
   syntax; its `json` is a table serialized as JSON, not a document with a shape of its own. What step
   6 hands over is not a table: it is a ticket identifier, an account record, a checklist of items each
   with a verdict, up to two follow-up pairs, and possibly a marked speculation. Flattening that into
   one CSV destroys exactly the structure the receiving side reads. Three shapes are missing and none
   of them exists in any form: a **text document rendered from a template**, a **JSON document with an
   author-defined shape**, and **more than one artifact produced by one run**.

4. **Nothing can check that an answer came back in the shape that was asked for.** Step 4 requires the
   returned checklist to carry exactly the declared items. `answer` declares a name and a type
   (ADR 013), and `type: dict` accepts any dictionary; no guard inspects keys. The company's checklist
   is therefore enforced by the wording of the question and by nothing else — the same finding the
   ADR-0083 measurement ended on, now reached from a second direction.

5. **The one thing that already works.** Step 2's exit — a `stop` that helps the caller and produces no
   deliverable — is legal today and needs nothing: a declared deliverable that was never produced
   records a `deliverable_missing` event and does not annul the completed run
   (`artifacts_export.py:49`). The bounded re-ask is `max_attempts` (ADR 013), already there and
   already proven by the ADR-0083 scenario.

## Where the judgment lives

Step 4 says "the model determines that a checklist item points at the problem". That judgment is the
answerer's, not the engine's: the engine publishes a question and routes on what comes back. This
scenario therefore does **not** depend on ADR 014 — it can be driven exactly the way the ADR-0083
scenario was already driven, by an agent answering published question blocks from outside (session
`2026-08-20-investigation-1`). ADR 014 would make the answerer a node instead of a caller; it changes
who runs the loop, not whether the flow is expressible.

What the scenario does put pressure on is the boundary the ADR-0083 measurement already named: an
answer whose shape matters is constrained by wording rather than by code. Gap 4 above is that finding,
in a flow a customer would actually run.

## Proposed as an exit condition of phase 2, and the document that would hold it

The proposal made in the triggering discussion: **running this scenario for real is a required
condition for leaving phase 2**, ahead of anything else that is open. The reasoning is that phase 2
was declared to be about work done by language models inside a defined process, and this is the first
flow where the process belongs to a business rather than to the test suite.

That proposal cannot be recorded as anything but a proposal today, and the reason is a finding of its
own: **no document in this repository holds the phase plan.** "Phase 2" appears only as sentences
inside ADR 007 §4, ADR 012, ADR 013, ADR 014 and ADR 015, and in two notes here. The closest thing to
a statement of its goal is one line in `adr-014` ("The first phase 2 goal is a workflow with a clearly
defined process in which language models do the work"), and the closest thing to a plan is the ordered
list at the end of `2026-08-19-adr0083-scenarios-coverage.md`, which is scoped to that note's
scenarios. Three of the documents that mention the phase are Accepted and therefore frozen.

So an exit condition has nowhere to be written that is neither a frozen ADR nor a note that by its own
README is explicitly not a decision. Either the phase plan gets a document and the map gains an entry
for it, or phase boundaries stay an oral tradition carried in ADR prose. This note does not settle
that; it records that the choice exists and is now blocking something concrete.

## What the sessions that take this on have to decide

1. **Whether the missing output shapes are one decision or three functions.** Text template, JSON
   document and several artifacts from one run look like three additions, but they share one question —
   what forms may a run hand its result out in, and who defines the shape — and answering that once is
   what keeps a fourth shape from being invented ad hoc later. The leading position from the triggering
   discussion is one ADR over the family, not three component tickets.
2. **Where a composed artifact name comes from** (gap 2): the smallest of its three options to
   implement and the largest to get wrong, since widening ADR 016 touches every function parameter in
   the engine.
3. **Whether a dictionary parameter is a component or a symptom.** An `init_dict_param` plus a setter
   is the obvious answer; the question worth asking first is why the bus grew list and deque support
   from a folder-walking template and nothing else, and what a second non-file flow would ask for next.
4. **Whether the checklist constraint is a guard or a declaration.** A guard that inspects keys is one
   component; declaring the shape of an answered dictionary in `answer` itself is a change to the
   ADR 013 contract. They are not the same size.
5. **What in the inventory is actually dead.** 13 file-info functions were written for one scan
   template. Removing any of them changes a public surface and belongs in its own `refactor/` session,
   after the additions above are decided — not folded into the work that adds things.
