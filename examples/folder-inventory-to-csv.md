# folder-inventory-to-csv

- **Identifier:** `folder-inventory-to-csv`
- **Class:** `4`
- **Answerers:** none — no step waits for an answer; the operator, a human or a calling program,
  binds the input and starts the run.
- **Input data:** `scan_root` (`Path`) — the folder to walk, bound as a workflow input; the tree
  behind it is whatever the operator points at.
- **Expected paths:** a queue-driven walk selects per entry: a file has its metadata row collected,
  a folder has its entries enqueued; an empty queue leaves the loop for the table write, and the
  written table is followed by the grouped report. A tree that holds no file reaches the table
  write with no rows.
- **Ends with:** end of workflow with the `file_scan_table` CSV and the `file_scan_report` document
  exported; failure under `pretty_table_no_data` when the walk found no file; failure under
  `pretty_table_artifact_exists` or `pretty_table_write_error` when the table cannot be written
  (not verified); failure under the `grouped_tables_*` codes when the report cannot be written
  (not verified).
- **ADRs exercised:** ADR 002, ADR 006, ADR 011, ADR 012, ADR 020, ADR 021

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
