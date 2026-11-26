# A digest of public technical documentation as the showcase run with a model

- **Date:** 2026-11-25
- **Trigger:** owner's proposal after the CI demonstration of roadmap step 17 was published: a second
  demonstration, this time with an `llm` node, on a task useful in its own right.
- **Status:** `promoted → ADR 023`; closed by session `2026-11-27-architecture-2`
- **Affected:** ADR 005, ADR 023, ADR 014 (the `llm` action and the providers), ADR 020 (template rendering and the
  output family), ADR 022 (the run report), the note `2026-11-21-run-report-and-public-showcase`, the
  note `2026-11-25-report-home-in-journal-details`, `docs/architecture/roadmap.md` (the showcase steps)

## The idea

A workflow collects the release notes of a project, or any other technical documentation, from a
list of public pages on one subject:

1. iterate over a list of URLs;
2. fetch each page and keep its text;
3. pass the text through an `llm` node with a declared context window and a task: pick out what
   matters and summarize it;
4. compose the summaries into one document and deliver it as a PDF.

The run is then published like the step 17 demonstration: the report of the session beside its
deliverable. Models are compared on a GPU with 36 GB of memory, on a time window the owner arranges,
and the one that serves the showcase best is chosen.

The step 17 demonstration shows that the engine runs and explains its path, but every run in it is
file housekeeping. A digest is an application a reader recognises, and it shows the parts of the
engine the current demonstration leaves out: a model call with its audited facts, a context bound,
a refusal handled as a value.

## What the engine has, and what it lacks

Has:

- iteration over a list: `init_deque_param`, `set_param_from_deque` and a guarded loop, as in
  `folder-inventory-to-csv`;
- the `llm` action with providers for OpenAI-compatible servers, LM Studio and Ollama, every call
  recorded, `context_overflow` classed as an error value;
- the split-and-accumulate branch of `folder-inventory-to-csv-chunked` for a text the model refuses
  as too large (`split_text_to_deque`);
- template rendering to an artifact (`render_template_to_artifact`) and text artifacts.

Lacks:

- **fetching a page.** No component reaches the network; the `llm` providers do, but only to a model
  server. A fetch is possible with the standard library (`urllib`), with its own questions: timeouts,
  redirects, size bounds, the error codes of a failed fetch.
- **text out of HTML.** The standard library has a parser (`html.parser`), not an extractor; what is
  "the text of a release-notes page" differs per site.
- **a PDF.** The standard library does not write one, and the core has two dependencies. A PDF needs
  either a new dependency, which needs its justification and approval, or a component in an external
  module that the `ComponentLoader` imports, keeping the core free of it, or a conversion outside the
  engine from an HTML or Markdown artifact the run delivers.

## Options for where the new parts live

| Option | What | Cost | Trade-off |
| --- | --- | --- | --- |
| A. Core components | a fetch function and an HTML text function in the core, standard library only | one or two implementation sessions, help entries, tests without the network | every operator gets them; the core takes on the network and its failure modes |
| B. An external module | fetch, extraction and PDF in a module of the example, loaded through the configuration | a module, its tests, its place in the repository decided | the core stays as it is, and the example proves the extension point; the module's dependencies are the example's, not the engine's |
| C. The deliverable is HTML or Markdown; a PDF is made outside the run | the run stops at a text artifact; a step of the demonstration workflow converts it | the conversion tool chosen in CI only | no PDF component at all; "the run delivers a PDF" is no longer true, the page says what made it |

## Where the run can happen

The step 17 demonstration runs in CI because it needs nothing but the checkout. This one needs a
model server. As first written, the note assumed a GitHub-hosted runner reaches none of the owner's;
the owner's answers below correct that.

- **Run where the GPU is, publish the result.** The run, its report and its deliverable are made on
  the model host and published afterwards. The published report then carries that machine's paths,
  which is where the note `2026-11-25-report-home-in-journal-details` stops being theoretical.
- **A self-hosted runner on the model host.** The workflow runs as today, started by hand. On a
  public repository a self-hosted runner executes whatever a workflow given to it says, so it must
  serve only workflows started by hand, never a pull request.
- **A hosted model API from CI.** No local GPU, a secret in CI and a cost per run; it measures a
  provider, not the local models the owner wants to compare.

## The owner's answers (2026-11-25)

- **Where the run happens: CI, against a model host on the internet.** The GPU machine is an Ollama
  server reachable over the internet; the `payment-reconciliation` consumer already runs against it.
  A GitHub-hosted runner can therefore reach it, and the demonstration can stay a workflow started by
  hand, as in step 17, with no self-hosted runner and no run made elsewhere. The endpoint is
  configuration of the environment: it lives in a CI secret and in no committed file.
- **Where the new parts live: option B.** The core is not touched. The fetch, the HTML text extractor
  and the PDF writer, with whatever library the PDF takes, are components of an external module
  loaded through the configuration, and their dependencies are the example's, not the engine's.
- **Which documentation:** something stable chosen for the demonstration, for example the release
  description of a Claude model.
- **The context window:** found by trying settings on the model host, not fixed in advance.
- **It is a class 4 example** in `examples/`, with its walkthrough.
- **The input:** pages that do not change. The extractor is debugged on them first, then the models
  are compared on the same input; two or three models are enough for a comparison of results.
- **The roadmap place:** to be decided; the owner sees it as good for the showcase. Decided in
  `2026-11-27-architecture-1`: phase 2 step 19, next after step 17, ahead of step 14; step 18 moved to
  phase 3.

## Closed by `2026-11-27-architecture-2`

- **Where the new parts live: revised to a shipped add-on package.** The owner's answer of 2026-11-25
  (option B, a module of the example) is replaced: the engine is to run something useful on its
  delivery, so the components ship in a second add-on package beside the provider adapters, the PDF
  library an optional extra. Decided as Draft ADR 023, with the first slice cut to what the digest
  needs and splitting by the model's window deferred.
- **The endpoint does reach a published page.** Every error text of the shipped adapters names the
  endpoint, and that text becomes the node's error message, which the journal, the records and the
  report carry. The demonstration guards it: the CI workflow searches the site for the host before
  the upload and fails the publication on a match. The adapters are not changed.
- **The comparison of the models** is split: the raw measurements stay outside the repository with
  the owner's other model measurements, the choice and its reason go into the session note of the
  implementation, and the page publishes the report of the chosen model.
- **The pages:** the release descriptions of a Claude model, as the owner proposed. A summary with a
  link to the original is published, never the fetched text itself: the prompt and reply artifacts
  of the `llm` node are not put on the page, and the chosen site's terms for automated fetching are
  checked once when the pages are chosen.
