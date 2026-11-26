# Session 2026-11-27-architecture-2

## Type
architecture

## Goal
Settle the open questions of the `documentation-digest-showcase` note and decide whether the external
module of roadmap step 19 needs an ADR.

## Completion criteria
- Each of the four open questions of the note is answered in this note with the alternatives weighed,
  their trade-offs and their cost, or explicitly left open with the reason.
- The ADR question is decided: an ADR opened as a Draft, or the reason none is needed recorded.
- The note records the answers and its `Status` reflects them.

## Scope boundaries
- No code, no workflow file, no example.
- The four untriaged notes left by `2026-11-27-architecture-1` are not triaged here.
- The fix of the report-home leak (`report-home-in-journal-details`) is not decided here.

## Status
`completed`

## Result
- Draft ADR 023, shipped content components as a second add-on package, opened with its registry row.
- The `documentation-digest-showcase` note records the four answers and is closed as
  `promoted → ADR 023`; its registry row moved to "Closed".
- `roadmap.md` row 19 rewritten: architecture done, the ADR 023 slice and the example pending.

## Decisions
1. **The components ship with the engine, in a second add-on package — ADR 023, Draft.** The owner
   revised the note's earlier answer (a module of the example): the engine is to run something
   useful on its delivery. Alternatives weighed:
   - *All in the core* — no configuration line; the PDF library becomes a core dependency and the
     core owns the network for every installation.
   - *Hybrid*, the standard-library parts in the core and PDF in an add-on — one capability in two
     places, the network still in the core.
   - *A second add-on package beside `workflow_engine_providers`*, PDF behind an optional extra —
     chosen: the core untouched, the ADR 014 §2 precedent repeated, one configuration line; costs a
     second supported package and the fetch's failure modes.
   - *A module of the example with a dependency group* — the delivery untouched, but an operator
     taking the wheel gets nothing.
   - *A workspace member in `examples/`* — the cleanest boundary, a second project and lock.
2. **An ADR is needed**, because the decision is about what the engine ships, not the layout of one
   example; without the revision a session-note decision would have sufficed.
3. **The first slice is the digest's**: fetch, the text of an HTML page, a PDF from a composed
   artifact. Splitting by the provider's context window is deferred to the Leaves open of ADR 023:
   it needs the provider configuration visible to a function and a size in tokens.
4. **The endpoint leak is real and guarded in CI.** The adapters' error texts name the endpoint and
   become the node's error message, carried by the journal, the records and the report. Weighed:
   adapters drop the endpoint (loses local diagnosis, covers one known path) against a CI search of
   the site for the host before upload (any path, a few lines); the CI guard was chosen.
5. **The model comparison is split**: raw measurements outside the repository with the owner's other
   model measurements, the choice and its reason in the implementation session note, the chosen
   model's report on the page. Weighed against every model's report published and the repository
   only.
6. **The pages are Claude model release descriptions.** A summary with a link is published, never
   the fetched text: the `llm` node's prompt and reply artifacts stay off the page, and the site's
   terms for automated fetching are checked once when the pages are chosen. Openly licensed pages
   were weighed and not needed.

## Open questions
- The PDF library (fpdf2, reportlab or another) — chosen and approved in the implementation session.
- Whether the report export puts the `llm` audit artifacts on the page — checked in implementation.
- The four untriaged notes: `authoring-extends-to-components`,
  `boundary-determinism-function-vs-model`, `published-contract-and-consumer-requests`,
  `storage-read-contract`.

## Next steps
1. ADR 023 into Implementing on `development`, then `feature/adr_023-shipped-content-components`:
   the package with fetch and HTML text, then the PDF submodule with its approved library.
2. The documentation-digest class 4 example with its walkthrough, listing ADR 023, and the model
   comparison on the owner's host.
3. The maintenance session adding the run and the endpoint guard to the `Demonstration` workflow.
4. A triage session for the four notes left, before the phase is closed.

## References
- Branch: `development`
- Opened: `docs/adr/adr-023-shipped-content-components.md`
- Changed: `docs/adr/README.md`, `docs/architecture/roadmap.md`,
  `docs/architecture/notes/2026-11-25-documentation-digest-showcase.md`,
  `docs/architecture/notes/README.md`
- Related: ADR 005, ADR 014, ADR 020, ADR 022; session `2026-11-27-architecture-1`
