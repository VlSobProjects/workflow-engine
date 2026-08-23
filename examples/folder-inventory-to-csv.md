# folder-inventory-to-csv

- **Identifier:** `folder-inventory-to-csv`
- **Class:** `4`
- **Answerers:** none — no step waits for an answer; the operator, a human or a calling program,
  binds the input and starts the run.
- **Input data:** `scan_root` (`Path`) — the folder to walk, bound as a workflow input; the tree
  behind it is whatever the operator points at.
- **Expected paths:** a queue-driven walk selects per entry: a file has its metadata row collected,
  a folder has its entries enqueued; an empty queue leaves the loop for the table write. A tree that
  holds no file reaches the table write with no rows.
- **Ends with:** end of workflow with the `file_scan_table` CSV exported; failure under
  `pretty_table_no_data` when the walk found no file; failure under `pretty_table_artifact_exists`
  or `pretty_table_write_error` when the table cannot be written (not verified).
- **ADRs exercised:** ADR 002, ADR 006, ADR 011, ADR 012

Walks a folder tree and writes a CSV inventory (path, size, MIME type, modified time, MD5) as the
`file_scan_table` deliverable.

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

Getting the CSV itself: see "Retrieving the result" in the root [`README.md`](../README.md).
