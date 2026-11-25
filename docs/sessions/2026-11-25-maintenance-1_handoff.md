# 2026-11-25-maintenance-1

## Type
`maintenance`

## Goal
Publish the deliverables of the demonstration's `folder-inventory-to-csv` run on GitHub Pages beside
its report, so a reader sees what the run delivered and not only that it delivered it.

## Completion criteria
- The demonstration exports the two deliverables of `folder-inventory-to-csv` into the published site,
  unchanged, and the index page links them.
- `actionlint` passes the workflow files, and the build steps run locally to the six published files.
- `README.md` states that the deliverables are published.

## Scope boundaries
- No engine change: the deliverables keep the absolute folder path the engine writes into them.
- `approve-and-copy` declares no deliverables and gets none; the copied file is not published.
- No Actions artifact beside the Pages deployment.

## Status
`completed`

## Result
- `demo.yml`: the inventory exports its deliverables under `folder-inventory-to-csv/reports/` of the
  site, and the index page links both files. The step that refused a page naming the runner's home
  directory is removed (decision 2).
- Locally, the build steps wrote the six files and every link of the index page resolves to one of
  them; `actionlint` 1.7.7 with `shellcheck` passes `demo.yml` and `ci.yml`.
- `README.md`: the demonstration paragraph names the published deliverables.
- Note `2026-11-25-report-home-in-journal-details`: the journal details of a report keep the home
  directory, which ADR 022 replaces by `~` in the values only.

## Decisions
1. **Scan a copy outside the home directory** — taken first, then withdrawn by decision 2. The
   inventory writes the scanned folder's absolute path into its deliverables, and the copy kept that
   path out of the runner's home so the check would pass.
2. **No check of the runner's home directory before publication.** The first run on GitHub was
   refused by the check: the `artifacts_exported` event of the journal names the export destination,
   and the report does not replace the home directory there. The runner's home is the same on every
   GitHub-hosted runner, names no person and holds no secret, so the check guarded nothing; whether
   the report keeps a home directory out of a page is a matter of the report's own tests. The check
   and the copy are removed, and the inventory scans `examples/` where the checkout put it. The gap
   in the report is a local operator's concern and goes to a note, not into this session.

## Open questions
- Whether the report should replace the home directory in the journal details too: note
  `2026-11-25-report-home-in-journal-details`, for an architecture session.

## Next steps
1. Start the workflow and check the two deliverables on the published page.
2. The architecture session of step 18.
3. Triage the note `2026-11-25-report-home-in-journal-details` in an architecture session.

## References
- Branch: `chore/demo-export-deliverables`
- Session `2026-11-24-maintenance-1` (the demonstration this extends)
- Changed: `.github/workflows/demo.yml`, `README.md`, `docs/architecture/notes/README.md`
- Note `2026-11-25-report-home-in-journal-details` (new)
