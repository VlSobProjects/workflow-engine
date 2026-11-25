# 2026-11-25-maintenance-1

## Type
`maintenance`

## Goal
Publish the deliverables of the demonstration's `folder-inventory-to-csv` run on GitHub Pages beside
its report, so a reader sees what the run delivered and not only that it delivered it.

## Completion criteria
- The demonstration exports the two deliverables of `folder-inventory-to-csv` into the published site,
  unchanged, and the index page links them.
- The published deliverables name no path under the runner's home directory, and the existing check
  still covers every published file.
- `actionlint` passes the workflow files, and the build steps run locally to the six published files.
- `README.md` states that the deliverables are published.

## Scope boundaries
- No engine change: the deliverables keep the absolute folder path the engine writes into them.
- `approve-and-copy` declares no deliverables and gets none; the copied file is not published.
- No Actions artifact beside the Pages deployment.

## Status
`completed`

## Result
- `demo.yml`: the inventory scans a copy of `examples/` under a neutral directory outside the runner's
  home and exports its deliverables under `folder-inventory-to-csv/reports/` of the site; the index
  page links both files. The first step writes its three paths in one grouped redirect.
- Locally, the build steps wrote the six files and every link of the index page resolves to one of
  them; `actionlint` 1.7.7 with `shellcheck` passes `demo.yml` and `ci.yml`. The home-directory check
  proves nothing locally, where the shell's home is spelled differently from the paths in the files;
  it is proven at the first run on GitHub.
- `README.md`: the demonstration paragraph names the published deliverables.

## Decisions
1. **Scan a copy outside the home directory, not mask the files.** The inventory writes the scanned
   folder's absolute path into the CSV and the text report, and the engine does not mask
   deliverables. Owner's choice over replacing the home directory in the exported files: the
   published files stay exactly as the engine wrote them, and the check keeps refusing a real leak
   instead of being satisfied by an edit.

## Open questions
None.

## Next steps
1. Merge into `development`, start the workflow, and check the two deliverables on the published page.
2. The architecture session of step 18.

## References
- Branch: `chore/demo-export-deliverables`
- Session `2026-11-24-maintenance-1` (the demonstration this extends)
- Changed: `.github/workflows/demo.yml`, `README.md`
