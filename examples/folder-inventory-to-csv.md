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
- **ADRs exercised:** ADR 002, ADR 006, ADR 011, ADR 012, ADR 020

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
