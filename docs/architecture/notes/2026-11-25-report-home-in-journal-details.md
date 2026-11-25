# The report keeps the home directory in the journal details

- **Date:** 2026-11-25
- **Trigger:** session `2026-11-25-maintenance-1`: the demonstration exported the inventory's
  deliverables, and the report of that session showed the runner's home directory in the journal.
- **Status:** `open`
- **Affected:** ADR 022 (the run report), ADR 018 (session read surfaces), ADR 020 (the export)

## The observation

ADR 022 replaces the home directory of the machine writing the report by `~` in the rendered values
and in the resolved text of a pending question, because "a path under a home directory names the
person who ran it". The journal tab renders the details of each event as they are stored, and
`artifacts_exported` names the export destination and the path of every exported file. `inputs_set`
names the inputs and their codecs only, never their values. Which other events carry a path is not
surveyed here.

An operator who exports under their home directory and publishes the report publishes their user
name, although the document states that the home directory is replaced. The masking the ADR gives a
reason for does not reach every place that reason applies to.

The demonstration in CI is not affected in any way that matters: the runner's home directory is the
same on every GitHub-hosted runner and names no one.

## Options

| Option | What | Cost | Trade-off |
| --- | --- | --- | --- |
| A. Leave it, and say so | The document and `README.md` state that the replacement covers the values only; `--no-values` does not help, the journal stays | a documentation change | the promise matches the behaviour; the leak stays for the operator who does not read the statement |
| B. Replace the home directory in the journal details too | the same replacement over every string of the event details | a superseding ADR, since ADR 022 is accepted and fixes the scope; code, tests, `README.md` | one rule for every rendered string; the journal no longer shows a detail exactly as stored, which the report otherwise does |
| C. Replace it everywhere the document renders a string | values, journal, the configuration of nodes as written | as B, wider | the simplest rule to state; touches the configuration, where a path is part of the definition the reader is shown |

## Open questions

- Is the journal of a report a rendering of values in the sense of ADR 022, or a record that is
  shown as stored?
- Which journal events carry a path, beside `artifacts_exported`?
- Should `--no-values` leave the paths of the journal details out as well?
