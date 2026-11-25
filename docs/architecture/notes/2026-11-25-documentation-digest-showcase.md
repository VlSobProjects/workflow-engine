# A digest of public technical documentation as the showcase run with a model

- **Date:** 2026-11-25
- **Trigger:** owner's proposal after the CI demonstration of roadmap step 17 was published: a second
  demonstration, this time with an `llm` node, on a task useful in its own right.
- **Status:** `open`
- **Affected:** ADR 014 (the `llm` action and the providers), ADR 020 (template rendering and the
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

The current demonstration shows that the engine runs and explains its path, but every run in it is
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
model server, and a GitHub-hosted runner reaches none of the owner's.

- **Run where the GPU is, publish the result.** The run, its report and its deliverable are made on
  the model host and published afterwards. The published report then carries that machine's paths,
  which is where the note `2026-11-25-report-home-in-journal-details` stops being theoretical.
- **A self-hosted runner on the model host.** The workflow runs as today, started by hand. On a
  public repository a self-hosted runner executes whatever a workflow given to it says, so it must
  serve only workflows started by hand, never a pull request.
- **A hosted model API from CI.** No local GPU, a secret in CI and a cost per run; it measures a
  provider, not the local models the owner wants to compare.

## Open questions

- Which documentation: a project whose release notes are public and whose licence allows a published
  summary, and how many pages per run.
- What the context window of the `llm` node is set to, and whether the comparison of models is a
  measurement this repository records or an owner's choice kept outside it.
- Is it a class 4 example in `examples/` with its own walkthrough, or a demonstration only?
- Is the page fetched when the run starts, or is a captured copy of the pages kept, so that two runs
  compare models on the same input?
- Where it stands on the roadmap against step 18 and step 14.
