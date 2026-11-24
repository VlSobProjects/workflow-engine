# 2026-11-24-maintenance-1

## Type
`maintenance`

## Goal
Add the public demonstration of roadmap step 17: a CI workflow started on demand that runs shipped
examples needing no model server and publishes their ADR 022 reports on GitHub Pages.

## Completion criteria
- `.github/workflows/demo.yml` runs on `workflow_dispatch` only, runs `folder-inventory-to-csv` to
  completion and `approve-and-copy` to its pause and, after a scripted answer, to completion, and
  writes three reports and an index page linking them.
- No page is published if one names the runner's home directory.
- The pages are deployed with `actions/upload-pages-artifact` and `actions/deploy-pages`; the write
  permissions for Pages are granted to the deploy job only.
- The build steps of the workflow, extracted from the file, run locally to the four pages.
- `README.md` links the demonstration page and names the workflow that writes it.

## Scope boundaries
- No engine change, no change to `report` or to the shipped examples.
- No run that calls a model, not even on the `fake` adapter, and no failed run.
- `ci.yml` and `secrets.yml` are not touched.

## Status
`completed`

## Result
- `demo.yml`: a build job runs the two examples with `--work-dir` under the runner's temporary
  directory, accepts exit code `2` as the pause of `approve-and-copy` and nothing else, writes the
  paused report through `--output` before `resume --answer`, then the completed one; an index page
  names the commit and the ref it was written from; a check refuses the publication when a page holds
  the runner's home directory; a deploy job publishes to the `github-pages` environment.
- The build steps, extracted from the workflow file and run locally, wrote the four pages; the
  reports replace the home directory by `~` and no page names the local user.
- `README.md`: the entry block links the demonstration page.

## Decisions
1. **Three reports: `folder-inventory-to-csv` completed, `approve-and-copy` paused and answered.**
   Owner's choice over adding `flatten-copy-tree`, a `fake`-adapter variant or a failed run: the loop
   and the pause are what a reader of the report has to see; the rest adds pages, not facts.
2. **`deploy-pages` over a `gh-pages` branch.** Nothing generated enters the repository's history and
   the workflow needs no `contents: write`; the cost is that Pages must be set to "GitHub Actions" as
   its source in the repository settings, by the owner.
3. **The index page is written by the workflow step, not committed as a file.** It is generated output
   of the run, and a committed HTML file would be a document outside the documentation map.

## Open questions
- The first run on GitHub has not been made: Pages is not yet enabled for the repository, and the
  `github-pages` environment may admit deployments from the default branch only.

## Next steps
1. Enable Pages with "GitHub Actions" as the source, merge into `development`, and start the
   workflow: `gh workflow run demo.yml --ref development`; check the published pages.
2. On `development`, mark step 17 done in `docs/architecture/roadmap.md` and add the registry row.
3. The architecture session of step 18.

## References
- Branch: `chore/public-demonstration`
- ADR 022 (Accepted), note `2026-11-21-run-report-and-public-showcase`
- Changed: `.github/workflows/demo.yml` (new), `README.md`
