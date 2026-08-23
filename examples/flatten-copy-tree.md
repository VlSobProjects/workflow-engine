# flatten-copy-tree

- **Identifier:** `flatten-copy-tree`
- **Class:** `4`
- **Answerers:** none — no step waits for an answer; the operator, a human or a calling program,
  binds the two inputs and starts the run.
- **Input data:** `source_root` and `target_dir`, both `Path`, bound as workflow inputs.
  **`target_dir` must already exist.**
- **Expected paths:** a queue-driven walk selects per entry: a file is copied into `target_dir` and
  its report row collected, a folder has its entries enqueued; an empty queue leaves the loop for
  the report write. A tree that holds no file reaches the report write with no rows (not verified).
- **Ends with:** end of workflow with the copied files and the `copy_report` CSV exported; failure
  at the copy node under `target_folder_not_found` when `target_dir` does not exist, or under
  `copy_failed` when a file cannot be copied (not verified); failure under `pretty_table_no_data`
  when the tree held no file (not verified), or under `pretty_table_artifact_exists` or
  `pretty_table_write_error` when the report cannot be written (not verified).
- **ADRs exercised:** ADR 002, ADR 006, ADR 011, ADR 012

Walks a folder tree and copies every file into a flat target directory, writing a copy report
(source, copied path, MD5) as the `copy_report` deliverable.

If the target directory does not exist, the first copy fails the `COPY_FILE` node with the error code
`target_folder_not_found`, the run stops as a failed workflow (exit code `3`) with that code under
`errors.COPY_FILE`, and no file is copied; create the directory and start again. A file that cannot
be copied fails the run the same way, under `copy_failed`.

```
workflow-engine run --workflow-file examples/flatten-copy-tree.json \
  --input "source_root:Path=<folder-to-copy>" --input "target_dir:Path=<destination-folder>" --json
```
