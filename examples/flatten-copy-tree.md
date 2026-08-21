# flatten-copy-tree

Walks a folder tree and copies every file into a flat target directory, writing a copy report
(source, copied path, MD5) as the `copy_report` deliverable.

- **Inputs:** `source_root` and `target_dir`, both `Path`.
- **Precondition:** **`target_dir` must already exist.**
- **Result:** the copied files and the `copy_report` deliverable.

If the target directory does not exist, the first copy fails the `COPY_FILE` node with the error code
`target_folder_not_found`, the run stops as a failed workflow (exit code `3`) with that code under
`errors.COPY_FILE`, and no file is copied; create the directory and start again. A file that cannot
be copied fails the run the same way, under `copy_failed`.

```
workflow-engine run --workflow-file examples/flatten-copy-tree.json \
  --input "source_root:Path=<folder-to-copy>" --input "target_dir:Path=<destination-folder>" --json
```
