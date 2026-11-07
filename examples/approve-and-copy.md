# approve-and-copy

- **Identifier:** `approve-and-copy`
- **Class:** `4`
- **Answerers:** one — the `ASK_APPROVAL` step, answered through `resume --answer` by whoever reads
  the published question block: a human at the command line or a program driving it. Every other
  step is the engine's own.
- **Input data:** `source_file` and `target_dir`, both `Path`, bound as workflow inputs.
  **`target_dir` must already exist.**
- **Expected paths:** the answer text selects the route: `approved` copies the file, `rejected`
  ends the run with nothing copied (not verified), a declared failure answer routes on its error
  code, and any other text asks the same question again until the two repeats after the first
  question run out.
- **Ends with:** end of workflow after the copy on `approved`, or with nothing copied on `rejected`
  (not verified); failure under `approval_failed` on a failure answer, under
  `max_attempts_exceeded` when the two repeats are spent, after the third question, or under `copy_failed` when the copy
  itself fails (not verified); until someone answers, the run is paused with the published question.
- **ADRs exercised:** ADR 002, ADR 006, ADR 012, ADR 013, ADR 016

Asks for a decision before it copies anything, which is what an `ask` node is for: the run stops, the
command reports a paused workflow (exit code `2`), and nothing else happens until someone answers.

```
workflow-engine run --workflow-file examples/approve-and-copy.json \
  --input "source_file:Path=<file-to-copy>" --input "target_dir:Path=<destination-folder>" --json
```

The paused result carries the question under `data.question`. Every presentation field is template
text, so the file and the size the previous node measured stand inside the instruction the answerer
reads rather than beside it:

```json
"question": {
  "node_id": "ASK_APPROVAL",
  "title": "Approve the copy",
  "instruction": "Decide whether '<file-to-copy>' (1.20 KB) may be copied. Answer 'approved' or 'rejected' as the answer text, and name the decision maker in 'reviewer'.",
  "options": ["approved", "rejected"],
  "answer": [{"name": "reviewer", "type": null, "required": true, "description": "Who made the decision"}],
  "error_catalogue": {"source_unreadable": "The file cannot be read, so no decision can be made."},
  "generic_error_code": "answer_failed"
}
```

Answer it with `resume --answer` (or `--answer-file <path>` for the same document in a file):

```
workflow-engine resume --session-id <SESSION_ID> --json \
  --answer "{\"status\": \"success\", \"values\": {\"reviewer\": \"me\"}, \"text\": \"approved\"}"
```

`approved` copies the file; `rejected` ends the run as a completed workflow (exit code `0`) with
nothing copied. An answer text that is neither sends the run back to the same node: this template
sets `max_attempts` to `2`, which counts the repeats after the first question — three questions in
all — and then fails under `max_attempts_exceeded`.

What the answer document may contain, what is refused, and what a `resume` without an answer does are
defined in "Answering an interactive workflow" in the root [`README.md`](../README.md).
