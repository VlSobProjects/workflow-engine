# folder-inventory-to-csv

- **Identifier:** `folder-inventory-to-csv`
- **Class:** `4`
- **Answerers:** none — no step waits for an answer, and the operator, a human or a calling program,
  binds the inputs and starts the run. The base definition is deterministic throughout. The three
  named variants below add `llm` nodes, where a model answers inside the run through a configured
  provider adapter and the run never stops for it; under `pytest` the `fake` adapter answers with
  scripted replies, so no test reaches a network.
- **Input data:** `scan_root` (`Path`) — the folder to walk, bound as a workflow input; the tree
  behind it is whatever the operator points at. The three variants add `described_formats`
  (`list`) — the MIME types whose files are read and described by the model.
- **Expected paths:** a queue-driven walk selects per entry: a file has its metadata row collected,
  a folder has its entries enqueued; an empty queue leaves the loop for the table write, and the
  written table is followed by the grouped report. A tree that holds no file reaches the table
  write with no rows. The variants add a second selection per file: a MIME type `described_formats`
  lists reaches the model, any other type and a file that does not read as text keep their row and
  say they were not described; in `chunked`, a file the model refuses as too large is described
  part by part instead; in `tiered`, the written table is followed by a second model step over all
  of it.
- **Ends with:** end of workflow with the `file_scan_table` CSV and the `file_scan_report` document
  exported; failure under `pretty_table_no_data` when the walk found no file; failure under
  `pretty_table_artifact_exists` or `pretty_table_write_error` when the table cannot be written
  (not verified); failure under the `grouped_tables_*` codes when the report cannot be written
  (not verified). The variants end the same way, each with the deliverables and the added failure
  codes named in its own section below.
- **ADRs exercised:** ADR 002, ADR 006, ADR 011, ADR 012, ADR 014, ADR 020, ADR 021, ADR 022

Walks a folder tree and writes two deliverables over the same collected rows (folder, file name,
size, MIME type, modified time, MD5): `file_scan_table`, one flat CSV for whatever reads it as
data, and `file_scan_report`, the same inventory composed for a human — one table per folder, the
folder path as its heading. One flat table over a whole tree is what the operator of this example
reported as unreadable, and the report is the answer (ADR 020).

Step by step:

```
workflow-engine init-new-session --workflow-file examples/folder-inventory-to-csv.json --json
workflow-engine set-input --session-id <SESSION_ID> --input "scan_root:Path=<folder-to-scan>"
workflow-engine resume --session-id <SESSION_ID> --json
```

Or in one shot:

```
workflow-engine run --workflow-file examples/folder-inventory-to-csv.json \
  --input "scan_root:Path=<folder-to-scan>" --json
```

Getting the files themselves: see "Retrieving the result" in the root
[`README.md`](../README.md); both deliverables are exported together.

## Reading the walk back

The walk is a loop: one pass of `POP_NEXT` / `EMIT_CUR_PATH` per tree entry, and either `COLLECT`
for a file or `ENQUEUE` for a folder. The state keeps one slot per node, so the next pass overwrites
the last one - after the run, `show-state` reports a single guard result for `EMIT_CUR_PATH`, the one
from its final pass. The walk itself is in the node records, one per concluded visit (ADR 021):

```
workflow-engine show-records --session-id <SESSION_ID>
```

```
Records of session <SESSION_ID> (27 of 27 records):
... INIT_QUEUE visit 1 attempt 1  function:init_deque_param  completed  -> node INIT_ROWS  writes: scan_queue (collections.deque, SET)
... SEED_QUEUE visit 1 attempt 1  function:enqueue_folder_entries  completed  -> node POP_NEXT  writes: scan_queue (collections.deque, EXTEND)
... POP_NEXT visit 1 attempt 1  function:set_param_from_deque  completed  -> node EMIT_CUR_PATH  guards: equals:empty=fail  writes: scan_queue (collections.deque, POP_LEFT), cur_path (builtins.str, SET)
... EMIT_CUR_PATH visit 1 attempt 1  function:echo_value  completed  -> node COLLECT  guards: is_output_exist_file=pass
... COLLECT visit 1 attempt 1  functions  completed  -> node POP_NEXT  writes: table_rows (builtins.list, APPEND)
```

Each line is one visit: the node with its visit and attempt ordinals, the action and the function it
ran, the status, the guards that were asked and how they answered, the transition that was taken, and
the parameters and artifacts the visit wrote - by name, codec and write mode, never a value. The path
each entry took is readable from the guards: `is_output_exist_file=pass` sent the entry to `COLLECT`,
`=fail` sent it to `ENQUEUE`.

`--node` narrows to one node, which is how many rows a walk collected and in which order:

```
workflow-engine show-records --session-id <SESSION_ID> --node COLLECT
```

```
Records of session <SESSION_ID> (4 of 27 records):
... COLLECT visit 1 attempt 1  functions  completed  -> node POP_NEXT  writes: table_rows (builtins.list, APPEND)
... COLLECT visit 2 attempt 1  functions  completed  -> node POP_NEXT  writes: table_rows (builtins.list, APPEND)
... COLLECT visit 3 attempt 1  functions  completed  -> node POP_NEXT  writes: table_rows (builtins.list, APPEND)
... COLLECT visit 4 attempt 1  functions  completed  -> node POP_NEXT  writes: table_rows (builtins.list, APPEND)
```

`--tail` bounds what is left, so the two compose as "the last n visits of this node"; the header says
how many records the answer carries out of how many the stream holds, so a bounded read never reads
as the whole trail.

The stream is a file of its own, `records.jsonl` beside `state.json` in the session directory: one
JSON object per line, appended and never rewritten. Nothing moved out of the state to make room for
it - the state holds what a resume needs, the trail holds what an explanation needs.

## Variants: a model in the walk

Three definitions ship beside the base one, each a run of its own rather than a mode of one file:

| Definition | What it adds | Deliverables |
| --- | --- | --- |
| `folder-inventory-to-csv-described.json` | A `Description` column written by a model, for the files whose format the input lists | `file_scan_table` |
| `folder-inventory-to-csv-tiered.json` | The same, plus a second model step composing an optimization proposal over the whole table | `file_scan_table`, `optimization_proposal` |
| `folder-inventory-to-csv-chunked.json` | The same, plus the split-and-accumulate branch for a file the model refuses as too large | `file_scan_table` |

All three keep the walk of the base definition and drop its `WRITE_REPORT` step: the description
belongs to the row, and the grouped report is a deliverable of its own that these variants do not
repeat. Among themselves they share eleven nodes — everything `described` has except its table
write — and `tiered` and `chunked` are that plus their own branch. Each is a definition of its own
on purpose, because a variant can then be named as the evidence of a gate and executed alone, and
the price is stated where it is paid: a fix to the walk is a fix in three files.

### Configuring a provider first

None of the three runs against a bare install. The `llm` node names a provider, and a provider is a
name in the engine configuration file, not something a definition carries — see "Calling a model" in
the root [`README.md`](../README.md). All three name the provider `local`, so the configuration file
needs a block of that name:

```json
"external_modules": ["workflow_engine_providers"],
"providers": {
  "local": {
    "adapter": "openai_compatible",
    "base_url": "http://127.0.0.1:1234/v1",
    "model": "<the model your server holds>",
    "options": {"timeout": 300}
  }
}
```

`src/workflow_engine_providers/example_config.json` carries the same two keys filled in three ways,
including the `lmstudio` adapter, which loads and unloads models on an LM Studio server instead of
only speaking to it.

Two things to settle before a real run:

- The prompts of the three variants ask for one sentence and nothing else. A very small model
  obliges less often than a large one, and what it answers lands in the column as it came — so the
  model the provider block names decides how readable the `Description` column is.
- One line has to be edited. `tiered` names its second model on the node itself, as the placeholder
  `"model": "a-publisher/a-larger-model"`. A node's `model` is a literal and resolves no reference,
  so a real identifier here would pin a shipped definition to one machine's model set. **The
  `tiered` variant does not run until that one line names a model the configured server actually
  has.** The other two name no model at all and take the one the provider block declares.

### `described`: a column the model writes

Two nodes are inserted between `EMIT_CUR_PATH` and `COLLECT`, and one beside them:

- `CLASSIFY_FORMAT` reads the MIME type of the file and asks `is_output_in_collection` whether
  `described_formats` lists it. A type that is listed goes on to `READ_FILE`, any other type goes
  to `NOT_DESCRIBED`.
- `READ_FILE` puts the text of the file on the bus as `file_text`. A file that is not there, does
  not decode as text, or cannot be read (`file_not_found`, `file_not_text`, `file_read_error`) goes
  to `NOT_DESCRIBED` as well — a binary file whose MIME type happened to be listed loses its
  description, not its row.
- `DESCRIBE` is the `llm` node. It sends the path and the text, asks for one sentence, and binds the
  reply to `file_description` under `format: "text"`. `record: true`, so the prompt and the reply of
  every call are artifacts of the run.
- `NOT_DESCRIBED` writes the literal `not described` into the same `file_description` parameter.

`COLLECT` is then the base node with `Description` in place of `MD5`, reading `file_description`:
what a row of an inventory the model read is about is worth more than its checksum. Both paths write
that parameter, so the row is the same shape whichever way the file went, and a tree of images
produces a full table in which every description says `not described`.

What `DESCRIBE` routes: `transient`, `rate_limited`, `timeout` and `llm_answer_invalid` go back to
the node itself, bounded by `max_attempts: 3`; `context_overflow` — a file the model will not read
at once — goes to `NOT_DESCRIBED`, which is what `chunked` replaces; anything else fails the run
under `description_unavailable`, the code this definition gives to a model that could not be reached
at all.

```
workflow-engine run --workflow-file examples/folder-inventory-to-csv-described.json \
  --input "scan_root:Path=<folder-to-scan>" \
  --input 'described_formats:list=["text/plain", "text/markdown"]' --json
```

Ends with end of workflow and the `file_scan_table` CSV; failure under `description_unavailable`,
or under the `pretty_table_*` codes of the base.

### `tiered`: a second, larger model over the finished table

`described`, and after `WRITE_TABLE` two more nodes:

- `PROPOSE` is an `llm` node over `${param.table_rows}` — the accumulated rows with their
  descriptions, rendered into the prompt as compact JSON by the single rendering rule of ADR 016. It
  asks for at most ten numbered points on what to archive, what looks duplicated and what belongs
  elsewhere, and binds the answer to `proposal_text`.
- `WRITE_PROPOSAL` writes that text as the `optimization_proposal` artifact.

The run therefore ends with two deliverables over the same walk: the CSV a machine reads and a
proposal a person acts on.

This is also where one definition uses both ways of choosing a model. `DESCRIBE` names none and
takes the model of the provider block — the small model that reads one file at a time. `PROPOSE`
names its own `model` on the node, because the whole table in one prompt is a different job from one
file. Two models, one provider, chosen by the graph rather than by a switch.

An oversized inventory fails `PROPOSE` under `inventory_too_large` rather than routing anywhere: at
that point there is nothing left to split that would not change what the proposal is about.

```
workflow-engine run --workflow-file examples/folder-inventory-to-csv-tiered.json \
  --input "scan_root:Path=<folder-to-scan>" \
  --input 'described_formats:list=["text/plain", "text/markdown"]' --json
```

Ends with end of workflow and both deliverables; failure under `description_unavailable`,
`inventory_too_large`, `proposal_unavailable`, the `text_artifact_*` codes of the proposal write, or
the `pretty_table_*` codes of the base.

### `chunked`: the file the model refuses, described part by part

`described`, except that `context_overflow` at `DESCRIBE` is not the end of that file's description
but the entrance to a loop of five nodes:

- `SPLIT_TEXT` splits `file_text` into a deque of parts of at most 2000 characters, breaking on the
  last paragraph or line break that fits. The budget counts characters and not tokens: the engine
  carries no tokenizer, which is exactly why the model's refusal is the signal in the first place.
- `INIT_PARTS` starts an empty `part_descriptions` list. It passes `allow_overwrite: true`, because
  a second oversized file in the same tree finds the list of the first one still there.
- `POP_CHUNK` takes the next part, or leaves the loop for `SUMMARIZE_PARTS` when the deque is empty.
- `DESCRIBE_CHUNK` is one `llm` call per part, and `APPEND_PART` appends what it answered.
- `SUMMARIZE_PARTS` is a last `llm` call over the accumulated part descriptions, and it binds the
  one `file_description` that reaches the `Description` column — the same column, filled the same
  way, so the table does not show which files took the long way.

The record stream does show it. One `DESCRIBE` visit ending in `context_overflow`, then one
`DESCRIBE_CHUNK` visit per part, then one `SUMMARIZE_PARTS` visit, each with the model and the token
counts of its own call in `details`.

A part that is still too large fails the run under `chunk_too_large`, and a set of part descriptions
too large to summarize fails under `parts_too_large`. Neither is split again: a budget that was
already wrong is not made right by halving it once more, and the honest answer is that the operator
lowers `chunk_size` or points the provider at a model with a larger window.

```
workflow-engine run --workflow-file examples/folder-inventory-to-csv-chunked.json \
  --input "scan_root:Path=<folder-to-scan>" \
  --input 'described_formats:list=["text/plain", "text/markdown"]' --json
```

Ends with end of workflow and the `file_scan_table` CSV; failure under `description_unavailable`,
`chunk_too_large`, `parts_too_large`, `parts_not_collected`, or the `pretty_table_*` codes of the
base.
