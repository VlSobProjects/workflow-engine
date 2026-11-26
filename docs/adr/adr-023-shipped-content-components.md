# ADR 023: Shipped content components as a second add-on package

## Status
Draft

## Active branch
—

## Context
A bare install of the engine can call a model (ADR 014) but cannot reach any input a model is useful
on beyond the local file system: no component fetches a page, none takes the text out of HTML, none
writes a document a reader opens outside a text editor. Every operator who wants a model to work on
documentation, release notes or any published text writes those components first, so the engine
offers nothing useful on its delivery.

Roadmap step 19, the documentation digest of the note `2026-11-25-documentation-digest-showcase`,
needs exactly these parts: fetch a list of public pages, keep their text, summarize it with an `llm`
node, deliver the summaries as one PDF. The note first answered that they live in a module of the
example, their dependencies the example's. Session `2026-11-27-architecture-2` revised that answer:
the parts are a capability of the delivery, not of one demonstration, so where they live and how
their dependencies are declared is a decision about what the engine ships.

Constraints:

- The core has two dependencies and prefers the standard library; a new dependency needs its
  justification and the owner's approval.
- The standard library fetches (`urllib`) and parses HTML (`html.parser`), but does not write a PDF.
- The extension point exists: ADR 005 loads configured external modules after the core, and ADR 014
  §2 already ships one officially supported add-on package, `workflow_engine_providers`, in the same
  wheel, loaded only when an installation names it.

## Consumer
The party that acts on this decision is an operator who installs the engine and runs a shipped
example against a local or a hosted model, naming the package in `external_modules` and nothing more;
and, at the end of that run, a human who reads the delivered document. The freeze-gate evidence is
class 4: the documentation-digest example of roadmap step 19, built in its implementation sessions,
whose walkthrough in `examples/` carries the scenario header, lists this ADR, and is registered in
the scenario registry when its branch merges. No scenario lists this ADR before that example exists.
The `payment-reconciliation` scenario reads text PDF files and declares its PDF library a dependency
of its own project, never of the core; this decision keeps that true and does not serve it yet.

## Decision

### 1. A second add-on package, not the core
The content components live in a package of their own beside `workflow_engine_providers` — working
name `workflow_engine_content` — shipped in the same wheel, imported by nothing in the core, and
loaded only through `external_modules` (ADR 005). The core gains no component, no dependency and no
network access. The provider package's place under ADR 014 §2 becomes the pattern for a shipped
add-on rather than a single exception.

### 2. Dependencies: the standard library, one optional extra for PDF
Everything that the standard library can do is written on it. Writing a PDF needs a third-party
library; it is declared as an optional extra of the distribution (`pdf`), never in the core
dependencies. The PDF components live in a submodule of their own that the configuration names
separately, so an installation without the extra that names it fails at load with a configuration
error (ADR 005), not in the middle of a run. The library itself is chosen and approved in the
implementation session that writes the component.

### 3. The first slice is the one the digest needs
- **Fetch a page** over `http` or `https` into a parameter or a text artifact, with a timeout, a
  bound on the size of the body and a bound on redirects; a failed fetch is an error value with its
  own code, routable by the guards of the node, never an exception.
- **The text of an HTML page**, on `html.parser`: the visible text with scripts, styles and markup
  dropped; no per-site extraction rules.
- **A document written as PDF** from a text or Markdown artifact the run already composed (ADR 020).

Splitting a text too large for the model stays the existing `split_text_to_deque` with a size the
workflow declares. Markdown output already exists through ADR 020 template rendering.

### 4. The fetch knows nothing of a site's terms
What may be fetched and published is the operator's responsibility, stated on the help surface of
the fetch component; the component neither reads `robots.txt` nor refuses an address.

## Alternatives considered
- **All in the core.** Available with no configuration line. Rejected: writing a PDF makes a
  third-party library a core dependency, and the core takes on the network and its failure modes
  for every installation, used or not.
- **Hybrid: the standard-library parts in the core, PDF in the add-on.** Rejected: one capability
  split over two places, and the network still enters the core.
- **A module of the example, its library in a dependency group** (the note's first answer). Keeps
  the delivery untouched. Rejected by the owner: the engine is to run something useful on its
  delivery, and a dependency group is not installed by an operator who takes the wheel.
- **A separate project in `examples/` as a workspace member.** The cleanest boundary. Rejected: a
  second project and lock for what is still one package of the same repository.

## Consequences
- Costs: a second supported package with its help entries and tests, the tests never reaching the
  network; one optional extra and its library; the project owns the failure modes of a fetch.
- Enables: the documentation digest of step 19 and any workflow over published text from a bare
  install plus one configuration line.
- Closes off: content components entering the core without superseding this decision.
- Leaves open: reading text out of a PDF; a report written as HTML; splitting by the context window
  a provider declares rather than by a declared size, which needs the provider configuration visible
  to a function and a size counted in tokens; per-site extraction rules.

## Related ADRs
- ADR 005 — the external-module loading this package relies on.
- ADR 014 — the first shipped add-on package, whose place this decision repeats; the `llm` node the
  components feed.
- ADR 020 — the composed text or Markdown artifact a PDF is written from.
- ADR 022 — the report published beside the deliverable of the demonstration.

## Implementation notes
None yet.

## Change log
- 2026-11-27: opened as Draft in session `2026-11-27-architecture-2`.
