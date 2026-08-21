# folder-inventory-to-csv

Walks a folder tree and writes a CSV inventory (path, size, MIME type, modified time, MD5) as the
`file_scan_table` deliverable.

- **Inputs:** `scan_root` (`Path`) — the folder to walk.
- **Result:** the `file_scan_table` deliverable.
- **Empty tree:** a tree that holds no file at all produces no table, and the run fails with the
  error code `pretty_table_no_data`.

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
