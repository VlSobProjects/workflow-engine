# The reconciliation that enters nothing it cannot prove

- **Identifier:** `payment-reconciliation`
- **Class:** `2`
- **Answerers:** code for everything with a fixed form — parsing the statements, the exact match,
  every guarantee check, the form filling and the receipt confirmation; a local model, through an
  `llm` node, where judgment is needed — reading a payment document whose layout code does not
  know, and scoring a match the exact branch could not make; a human, through `ask` nodes, at two
  gates — the final submit of the certain entries, and the review of every scored match. The
  evaluation harness is not an answerer: it reads the run after the fact.
- **Input data:** a generated and labelled set, per variant: payment documents — orders and
  receipts — as text PDF files in several layouts, each naming a payer account, a payee account, an
  amount and a currency; account statements of several banks as PDF files in each bank's fixed
  layout, with account numbers and a statement period; card statements with no account number and
  euro amounts only; and the labels — for every payment document the statement entry it belongs
  to, or none. The set lives in the POC repository. Real documents are never input here: a run on
  real data happens only on a machine at the firm, with a local model on that machine.
- **Expected paths:** the certain path, where code matches the accounts, the amount and the date
  and every guarantee holds; the scored path, where the exact match fails and a model scores the
  candidates of that date; the meaning path, where a case code cannot recognise by form — a card
  statement with no payer account — is recognised by a model step before it falls to unmatched;
  the withheld path, where a guarantee check refuses an extracted field or a coverage gap, and a
  match that would otherwise be certain is scored instead; unmatched; the gated entry, paused for
  the human; the review loop over the scored matches, bounded by `max_visits`; failure when a
  reply or the provider fails past the retry bound. Each path is selected by its variant. Details
  in the body.
- **Ends with:** end of workflow with the reconciliation report exported as the deliverable — the
  certain matches with their confirmed receipts, the scored matches with the human's verdict, the
  unmatched documents with the reason — and, beside it, the machine-readable result the
  evaluation reads; the human gates are pauses, not ends; failure under `llm_answer_invalid` or a
  provider error class when `max_attempts` exhausts.
- **ADRs exercised:** ADR 005, ADR 006, ADR 011, ADR 012, ADR 013, ADR 014, ADR 016, ADR 017,
  ADR 018, ADR 020, ADR 021

## The consumer

A small accounting firm reconciles payment documents against bank statements by hand: a person finds
the accounts, the amount and the currency in the payment document, searches the statements for the
entry, marks it and types it into a web back office. The POC that automates this is built by a
project of the owner outside this repository, on the engine as it stands; the desk letter EX-17
(2026-10-05, questions on a reconciliation POC built on workflow-engine) brought the task here and
this document is where it landed. The recipient of a run is the person who reconciled by hand: they
get the certain entries filled in and waiting for their submit, the scored matches side by side with
the evidence, and the unmatched documents with the reason — never an entry they did not confirm.

The scenario is of the shape `purpose.md` names — fetch, judge, decide, branch, hand over — with
two differences from the exit scenario `load-test-triage`: the run loops over documents instead of
reading one dataset, and the human answers in the middle of the run, not only at its end. Both are
exercised by the shipped examples already: the deque loop of `folder-inventory-to-csv`, the `ask`
gate of `approve-and-copy`. It consumes the phase 1 and phase 2 core and pulls on nothing of
phase 3: every definition here is hand-written. Whether it also stands as the live scenario of the
publication phase is the roadmap's decision, recorded below as an open one.

## What ships where

The core stays as it is. Everything that knows a bank, a document layout, a back office or a
probability ships as an external module of the POC (ADR 005), loaded through `external_modules`
like the provider package.

| Module | What it does | Component kind | Size |
| --- | --- | --- | --- |
| PDF text extraction | The text of a text PDF into a parameter | function; a PDF library is a dependency of the POC, never of the core | small |
| Statement parsers, one per bank | A statement file into typed entries — date, counterpart account, amount, currency, message — plus the account number and the period of the statement | functions, code only; the layout of a bank is fixed | small per bank |
| Payment record extraction | A payment document into the typed record — payer account, payee account, amount, currency, date, message | an `llm` node with a `json` answer declaration; code first for the layouts it knows | medium: the prompt, and the guarantees below |
| Guarantee validators | The account appears verbatim in the PDF text; the IBAN checksum holds; the date falls inside a statement period; the statements cover the period with no gap; exactly one candidate entry remains | validators behind `function_name` guards | small each, the list grows with the cases |
| Exact matcher | Payer account, payee account, amount, date against the parsed entries | function | small |
| Agent matcher | The entries of that date against the payment document, a probability and a comment back | an `llm` node with a `json` answer; a validator turns the probability into a routable threshold | medium: the prompt, the answer shape, the calibration |
| Entry step | Fills the back-office form for the certain matches and stops before submit | function driving a browser; the browser must outlive the paused engine process | medium to large: the back office has no data-entry API and has not been seen |
| Receipt confirmation | Subscribes to the back office's event API and confirms that an entry landed | function with a bounded wait | small to medium, depending on the API |
| Report composition | The reconciliation report for the person and the result file for the evaluation | ADR 020 functions over the collected parameters; a POC function if a shape needs iteration | small |
| Data generator | The labelled set: documents in several layouts, statements per bank, planted cases per variant | outside the run, in the POC | medium: the hidden cost of the evaluation contour |
| Evaluation harness | Reads a finished run and computes the metrics | outside the run, in the POC | medium |

Reading amounts that are only an image is a later stage: the `llm` node carries text and nothing
else, and an image channel is the note `2026-08-28-rendered-panels-as-model-input`, an ADR across
the action, the adapter contract and the record channel.

## The flow shape

- **Fetch.** Start parameters (ADR 012) point the run at the folder of payment documents and the
  folder of statements. The statement parsers read every statement into typed entries on the bus;
  a coverage validator checks that the statements cover the period with no gap and records the
  result as a parameter, because "only one payment on that date" is a guarantee only under full
  coverage. The payment documents fill a deque, the loop pattern of the shipped inventory example.
- **Extract.** Per document, code reads the text and tries the layouts it knows. Where none fits,
  an `llm` node reads the text into the typed record under a `json` declaration — the model sees
  the document text and nothing else (ADR 016). Either way the record then passes the guarantee
  validators as `validators` of the node: the accounts verbatim in the text, the IBAN checksums, the
  date. A record that fails a guarantee is not discarded: the failure code routes the document to
  the scored path with the failed check named, because an extraction the code cannot vouch for
  must not feed the certain path.
- **Match exactly.** Code searches the entries for the payer account (unless the statement is a
  card statement), the payee account, the amount and the date. One candidate under full coverage,
  every guarantee held, is a certain match, appended to the certain list. Zero or several
  candidates route onward.
- **Match by meaning.** Where the case has a recognisable meaning but no matching form — a card
  statement with no payer account, a currency known only roughly — a step with a model prompt goes
  in before the document falls to unmatched. The agent matcher is an `llm` node that receives the
  entries of that date and the payment record, and answers a probability and a comment. A certain
  match may rest on a model, but only when a check proves it: one payment of about that amount to
  that account on that date, a payment message or an identifier present in both documents. The
  check is code, and often far cheaper than the match. Without such a proof the match carries its
  score and goes to the scored list; a probability below the declared floor goes to unmatched. The
  threshold is a registered validator, because the core's value guards compare text and a model is
  never a guard.
- **Loop.** The head of the loop pops the next document; `max_visits` on the loop head bounds the
  run beside the engine's node budgets. Every matching step reruns on every earlier case when a
  step is added: the labelled set is the regression.
- **Enter behind the gate.** After the loop the entry step fills the back-office form for every
  certain match and stops. An `ask` node then pauses the run with the filled entries in its
  presentation; the person presses the final submit in the back office and answers the question.
  The confirmation function listens for the receipt-created event and the run records which
  entries landed; an entry that was not confirmed within the wait is reported, not assumed.
- **Review.** The scored matches come after the entries. One `ask` node per match presents the
  statement line, the payment document and the filled form side by side; the person accepts or
  rejects; the answer is routed by guards like any other output (ADR 013) and collected with
  `collect_answer` (ADR 015). At the first stage the person reviews every match that is not certain.
- **Hand over.** The report node composes the deliverable (ADR 020): the certain entries with
  their receipts, the reviewed matches with their verdicts, the unmatched documents with the
  reason each fell through. Beside it a machine-readable result file carries, per document, the
  path taken, the match made, the probability where one was stated, and the human's verdict — the
  file the evaluation reads. A provider failure past `max_attempts` fails the run under its code;
  what was collected before it is in the state and the records.

## Certain or scored

A match is either certain or carries a confidence score, and the engine enforces the difference:
the certain path is reachable only through guards, so a wrong match cannot pass on its own. The
guards are code over the extracted fields and the parsed entries, never a model's statement about
itself. The guarantee covers the extraction, not only the match: an account a model read is checked
verbatim against the PDF text, its checksum is checked, the date is checked against the statement
period, and the uniqueness claim is made only under proven coverage. An entry without a person
happens only on the certain path; every other match is seen by a person before it is entered.

## The evaluation contour

The harness lives in the POC and reads the run; the engine records and does not judge
(`purpose.md` boundaries). What it reads:

- the result file the report node writes as a declared deliverable (ADR 011), which carries the
  values — the records carry names and codec names and never a value (ADR 021);
- the node records through `show-records --json`: the path per document, the visits and attempts,
  the guards asked and their answers, the model and status of every call;
- the prompts and replies as artifacts under `record: true`, where a wrong match is traced back.

What it computes, per run on the labelled set: the share of documents matched without a person;
the wrong matches, split by path, with the certain path required to carry none; the missed matches;
and the calibration of the agent matcher — the stated probability against the label, by bucket. A
regression run happens whenever a model, a prompt or a matching step changes, and the `fake`
adapter is the reference: scripted replies per variant give a deterministic route and a
deterministic result, so a model run is a distance from a known point — the protocol of the drift-B
section of `load-test-triage`, reused.

## Fail closed

No document leaves the office: a run on real data must not reach a cloud model. Today the core
holds this by configuration and not by enforcement — a node names a provider, the provider block
names the endpoint, and a configuration whose every `base_url` is a loopback address with no
`api_key_env` cannot go out. What proves it is a test, and the POC owns it: an engine configured
from the POC's own file, the network patched below the adapter, every variant run, and the
assertion that no call left the loopback. Whether the core should refuse a non-local endpoint
itself is an open decision below.

## Expected paths

1. **Certain.** A payment document in a known layout, one entry with the payer account, the payee
   account, the amount and the date, full coverage; code matches, every guarantee holds, the entry
   is filled and waits for the submit; the receipt event confirms it. The reference variant.
2. **Certain through a model.** A layout code does not know; the `llm` extraction yields the
   record, the guarantees hold verbatim, the exact match is unique. Same end as path 1; the records
   show the model call on the extraction node.
3. **Scored.** Two candidate entries, or an amount off by a rounding of a currency rate; the exact
   match fails, the agent matcher scores the candidates, the match waits for the review. Variants
   per cause.
4. **Meaning.** A card statement: no payer account, euro amount only; the exact matcher cannot
   apply, the meaning step recognises the one payment of about that amount to that account on that
   date, the uniqueness check proves it, and the match is certain; without the proof it is scored.
5. **Withheld.** A model-extracted account that is not verbatim in the text, an IBAN whose checksum
   fails, a date outside every statement period, or a coverage gap: the guarantee refuses, and a
   match that looked certain is scored with the failed check named.
6. **Unmatched.** No candidate on that date, or a score below the floor; the document is reported
   with the reason.
7. **Review loop.** The scored matches of a run reviewed one by one; the person's verdicts
   collected; the loop bounded by `max_visits`.
8. **Entry not confirmed.** The person submits, the receipt event does not arrive within the wait;
   the report states which entries were confirmed and which were not.
9. **Failure.** A reply that never parses (`llm_answer_invalid`) or a `permanent` refusal past
   `max_attempts`; scripted with the `fake` adapter, no dataset needed.

## Stages

The first stage reads text PDF files only, parses statements by code, matches by code, enters
behind the gate, and runs the evaluation on generated data; a person reviews every match that is
not certain. The meaning steps are added one case at a time, each on the evidence of what stayed
unmatched, each rerunning the earlier cases. Images come later, with the image channel.

## Open decisions the scenario still lacks

1. **Fail closed in the core.** A provider allow-list — only loopback or named hosts — would be a
   sixth key of the provider block, which ADR 014 refuses today; so it is an ADR, small, that the
   POC's test may make unnecessary. Decided when the real-data run is planned.
2. **A numeric comparison guard.** The core compares text; a threshold on a float is a registered
   validator. Whether a `greater_than` guard enters the core is decided by a second scenario that
   needs it, under ADR 002.
3. **The browser and the pause.** The engine is a process that returns at an `ask`; the browser
   that holds the filled form must be launched detached and outlive the call, or the entry step
   writes the filled form as a file and the person fills the back office from it. The first stage
   may take the second form; the back office decides.
4. **The publication gate.** The letter proposes this scenario as the live scenario of the
   publication phase in place of the load-rig run. That is a roadmap decision for an architecture
   session; this document does not make it.
5. **The run size.** A loop of about ten nodes per document meets the default hard cap of a
   thousand nodes at about a hundred documents; the cap is raised in the configuration file, and
   the note `2026-08-19-hard-node-cap-scoping` waits for numbers like these.
6. **Where the generated data lives.** In the POC repository, by size; the real documents
   nowhere but at the firm.
