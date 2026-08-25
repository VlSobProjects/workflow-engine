# reorganize-folder

- **Identifier:** `reorganize-folder`
- **Class:** `4`
- **Answerers:** none — no step waits for an answer. The operator binds the inputs and starts the
  run; the two judgment steps are `llm` nodes the engine calls itself through a configured provider
  adapter, a small call per file and one larger call over the whole inventory. Under `pytest` the
  `fake` adapter answers with scripted replies, so no test reaches a network.
- **Input data:** `scan_root` (`Path`) — the folder to plan a reorganization for; `categories`
  (`list`) — the closed list of category names the model must sort every file into, for example
  `["documents", "code", "images", "data", "other"]`. The list feeds the classification prompt, the
  decision prompt and the guard that checks the decision's counts.
- **Expected paths:** the plan path — the tree is walked, every file hashed, collected and
  classified, duplicates grouped by content hash in code, and the decision step answers with the
  plan; the re-ask path — the decision binds cleanly but the keys of `counts_by_category` are not
  drawn from `categories`, the `is_answer_keys_valid` guard refuses, and the node is asked again,
  bounded by `max_attempts`; the retry path — a `transient`, `rate_limited`, `timeout` or
  `llm_answer_invalid` reply retries the calling node under the same bound; the refusal path — a
  tree holding no file ends the run before a single model call.
- **Ends with:** end of workflow with the `reorg_plan` document and the `inventory_table` CSV
  exported; failure under `nothing_to_plan` when the walk found no file; failure under
  `max_attempts_exceeded` when the decision never fits its declaration; failure under
  `scan_root_missing`, `queue_lost`, `hash_unavailable`, `row_unavailable`, `grouping_lost`,
  `file_unclassifiable`, `categories_lost`, `duplicates_lost`, `inventory_too_large`,
  `plan_unusable`, `table_unwritten` or `plan_unwritten` when the step each code names cannot do
  its work (not verified except where the test suite says otherwise).
- **ADRs exercised:** ADR 002, ADR 006, ADR 011, ADR 012, ADR 014, ADR 016, ADR 020, ADR 021

Audits a folder tree and delivers a reorganization plan in two forms at once: prose a person
reviews, and a machine-readable moves dictionary a later run can act on. The split of labor is the
engine's method in miniature: code does everything checkable — walks the tree, hashes every file,
groups identical files by content hash, counts the groups — and the model does only the judgment,
sorting files into the configured categories and composing the plan. The model is told the
duplicates; it never gets to find them.

Step by step:

```
workflow-engine run --workflow-file examples/reorganize-folder.json --json \
  --input "scan_root:Path=<folder-to-plan>" \
  --input "categories:list=[\"documents\", \"code\", \"images\", \"data\", \"other\"]"
```

The run needs a configured provider named `local` (see "Calling a model" in the root
[`README.md`](../README.md)). It walks the tree breadth-first on a deque, and per file: an MD5
hash (`HASH_FILE`), a table row — folder, name, size, MIME type, MD5 (`COLLECT`) — the hash group
(`APPEND_HASH`, `append_to_dict_key`: files sharing a hash gather under it), and one small model
call sorting the file into a category (`CLASSIFY`), keyed to its path with `set_dict_item`
(`SET_CATEGORY`). When the queue is empty, `filter_dict_by_value_size` keeps the hash groups
holding more than one path — those are the duplicates, established in code — and the inventory
table is written. Only then the decision step (`DECIDE`) reads everything the run collected and
answers with three declared values: `plan_text`, the prose; `moves`, a dictionary from source path
to target folder; `counts_by_category`, a dictionary the `is_answer_keys_valid` guard checks
against `categories` before the answer lands — a decision that invents a category is asked again,
not recorded. The plan document is rendered from the authored template
`reorganize-folder-plan.tmpl` beside the definition (ADR 020), interpolating the prose and the
three dictionaries (ADR 016).

The deliverables:

- `reorg_plan` (`reports/reorg_plan.md`) — the plan: the model's prose, the machine-readable
  moves, the counts per category and the duplicate groups.
- `inventory_table` (`reports/inventory_table.csv`) — the flat inventory the plan was made from,
  one row per file including its MD5.

## The applying half is a later variant

This definition plans and stops: nothing is moved, nothing is deleted. The applying half — the
operator confirming the plan through an `ask` step, a deterministic validation of every move
against the file system, and the moves and deletions themselves — is planned as a named variant
beside this definition and does not ship yet. Until it does, the `moves` dictionary and the
duplicate list in the plan are the contract that variant will consume.

## What the tests cover

`tests/test_reorganize_folder_example.py` runs the shipped definition end to end on the `fake`
adapter: the plan path with a planted duplicate pair (identical content, different names and
folders), the shared hash in the table, one call per file plus one decision, the re-ask on
invented `counts_by_category` keys, `max_attempts_exceeded` when the keys never fit, and the
refusal of a file-less tree before any model call.
