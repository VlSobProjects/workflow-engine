# Sessions

A session is one narrow piece of work with a declared goal and a declared end.
Every session produces exactly one note in this directory.

## Session types

Closed list. A session has exactly one type.

| Type | Used for |
| --- | --- |
| `architecture` | Decisions captured as ADRs |
| `implementation` | Code changes |
| `documentation` | Documentation and rules |
| `investigation` | Research that changes no code |
| `maintenance` | Dependencies, tooling, repository hygiene |

## File naming

`YYYY-MM-DD-<type>-<n>_handoff.md`

- The date is the day the session started.
- `<type>` is the session type from the list above.
- `<n>` counts the sessions of that type on that day, starting at `1`, and is always present.
- Example: `2026-08-02-documentation-1_handoff.md`

The file name carries no description on purpose. Do not infer the content of a session from its name.
To find a session, read the registry below; sessions of one type are read in order.

## Lifecycle

1. At the start, create the session file with its type, goal and completion criteria.
2. During the session, keep the scope inside those criteria.
3. At the end, complete the file with the result, the decisions and the next steps.
4. Close the session with a git commit that includes the session note and related changes. If a session
   intentionally ends without a commit, state that explicitly in the session note with the reason.

A session that is interrupted still leaves its file, marked `interrupted`.

## Where it lives

- The session file is written in the working branch and lands with the work it describes.
- A session that produces no code still uses a branch, normally under `docs/`.
- The registry row below is added on `development` when the branch is merged.

## Content limits

- Record facts, decisions and next steps. Do not retell the course of the work.
- No code dumps, no command output, no logs.
- No local paths and no machine-specific facts: see `docs/rules/documentation-rules.md` §8.
- If the scope grew during the session, record the split and leave the rest to the next steps.

## Registry

The registry is the only index of sessions. The file names carry no description, so a session that is
missing from the registry is effectively lost. Add the row when the branch is merged.

- A row is one sentence; the facts are in the note.
- `ADR` lists the ADRs the session worked on, or `—`; the sessions of one ADR are read in date order.
- `Status` is `completed` or `interrupted`. An `interrupted` session must be picked up or explicitly
  closed before related work continues.
- The registry lists the current phase (`docs/architecture/roadmap.md`). When a phase closes, its rows
  move to their own file in this directory; the session files are not moved.

| Phase | Rows |
| --- | --- |
| 1 | [phase-1.md](phase-1.md) |
| 2 | below |

| Date | Type | Summary | ADR | Status | Branch | Link |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-08-19 | architecture | Closed the `v0.1.0` release, set phase 2 as additive, opened Draft ADR 013 and ADR 014 | ADR 013, ADR 014 | completed | development | [2026-08-19-architecture-1_handoff.md](2026-08-19-architecture-1_handoff.md) |
| 2026-08-19 | architecture | Settled the five open points of ADR 013 and moved it to Implementing | ADR 013 | completed | development | [2026-08-19-architecture-2_handoff.md](2026-08-19-architecture-2_handoff.md) |
| 2026-08-19 | implementation | Implemented ADR 013: the `ask` node, the published question block and `resume --answer` | ADR 013 | completed | feature/adr_013-interactive-exchange | [2026-08-19-implementation-11_handoff.md](2026-08-19-implementation-11_handoff.md) |
| 2026-08-19 | implementation | Let a path argument accept the `Path` a codec-typed input resolves to | ADR 012 | completed | fix/path-args-accept-path | [2026-08-19-implementation-12_handoff.md](2026-08-19-implementation-12_handoff.md) |
| 2026-08-19 | implementation | Attributed a written parameter to the node that produced it | ADR 006 | completed | fix/param-write-provenance | [2026-08-19-implementation-13_handoff.md](2026-08-19-implementation-13_handoff.md) |
| 2026-08-19 | implementation | Gave the three text renderings of a state value one POSIX rule | ADR 008 | completed | fix/posix-value-rendering | [2026-08-19-implementation-14_handoff.md](2026-08-19-implementation-14_handoff.md) |
| 2026-08-19 | implementation | Made a bounded accumulating loop expressible with `append_to_param` and a size guard | ADR 013 | completed | feature/bounded-accumulating-loop | [2026-08-19-implementation-15_handoff.md](2026-08-19-implementation-15_handoff.md) |
| 2026-08-20 | architecture | Opened Draft ADR 015: a registered function may run on an accepted answer | ADR 015 | completed | development | [2026-08-20-architecture-1_handoff.md](2026-08-20-architecture-1_handoff.md) |
| 2026-08-20 | documentation | Wrote down the commit message form | — | completed | docs/commit-message-template | [2026-08-20-documentation-1_handoff.md](2026-08-20-documentation-1_handoff.md) |
| 2026-08-20 | documentation | Made the commit message subject to confirmation (general rule 12) | — | completed | docs/commit-confirmation-rule | [2026-08-20-documentation-2_handoff.md](2026-08-20-documentation-2_handoff.md) |
| 2026-08-20 | documentation | Kept machine-specific facts out of committed documentation (documentation rule 8) | — | completed | docs/no-machine-specific-facts | [2026-08-20-documentation-3_handoff.md](2026-08-20-documentation-3_handoff.md) |
| 2026-08-20 | investigation | Built the ADR-0083 flow as a conformance scenario and ran it scripted and agent-driven | ADR 013 | completed | test/adr0083-scenario-flow | [2026-08-20-investigation-1_handoff.md](2026-08-20-investigation-1_handoff.md) |
| 2026-08-20 | architecture | Settled the seven open points of ADR 015 against the ADR-0083 evidence | ADR 015 | completed | development | [2026-08-20-architecture-2_handoff.md](2026-08-20-architecture-2_handoff.md) |
| 2026-08-20 | architecture | Opened Draft ADR 016: references resolve inside template text | ADR 016 | completed | development | [2026-08-20-architecture-3_handoff.md](2026-08-20-architecture-3_handoff.md) |
| 2026-08-20 | architecture | Opened Draft ADR 017: a per-node `max_visits` cap | ADR 017 | completed | development | [2026-08-20-architecture-4_handoff.md](2026-08-20-architecture-4_handoff.md) |
| 2026-08-20 | implementation | Implemented ADR 015: `function_name` on `ask`, run on the accepted answer before the guards | ADR 015 | completed | feature/adr_015-computation-inside-an-interactive-node | [2026-08-20-implementation-1_handoff.md](2026-08-20-implementation-1_handoff.md) |
| 2026-08-20 | architecture | Settled the open points of ADR 016: every presentation field of `ask` is template text | ADR 016 | completed | development | [2026-08-20-architecture-5_handoff.md](2026-08-20-architecture-5_handoff.md) |
| 2026-08-20 | implementation | Implemented ADR 016: `${...}` references in the presentation fields of `ask` | ADR 016 | completed | feature/adr_016-reference-interpolation-in-text | [2026-08-20-implementation-2_handoff.md](2026-08-20-implementation-2_handoff.md) |
| 2026-08-20 | implementation | Implemented ADR 017: `max_visits` refused on entry under `max_visits_exceeded` | ADR 017 | completed | feature/adr_017-per-node-visit-cap | [2026-08-20-implementation-3_handoff.md](2026-08-20-implementation-3_handoff.md) |
| 2026-08-20 | investigation | Re-measured the ADR-0083 coverage note against ADR 015–017 | ADR 015, ADR 016, ADR 017 | completed | docs/adr0083-coverage-remeasure | [2026-08-20-investigation-2_handoff.md](2026-08-20-investigation-2_handoff.md) |
| 2026-08-20 | implementation | Rewrote the shipped `ask` flows with the values inside the sentence | ADR 016 | completed | refactor/adr_016-values-inside-the-sentence | [2026-08-20-implementation-4_handoff.md](2026-08-20-implementation-4_handoff.md) |
| 2026-08-20 | architecture | Decided that the surfacing and accumulating post functions go into the core under ADR 015 | ADR 015 | completed | development | [2026-08-20-architecture-6_handoff.md](2026-08-20-architecture-6_handoff.md) |
| 2026-08-20 | implementation | Gave the ADR 015 stage `echo_answer` and `collect_answer` | ADR 015 | completed | feature/adr_015-post-function-components | [2026-08-20-implementation-5_handoff.md](2026-08-20-implementation-5_handoff.md) |
| 2026-08-20 | architecture | Drafted ADR 018: bounded session read surfaces | ADR 018 | completed | development | [2026-08-20-architecture-7_handoff.md](2026-08-20-architecture-7_handoff.md) |
| 2026-08-21 | implementation | Implemented ADR 018: `show-state`, `list-parameters`, `show-parameter`, `show-journal` | ADR 018 | completed | feature/adr_018-session-read-surfaces | [2026-08-21-implementation-1_handoff.md](2026-08-21-implementation-1_handoff.md) |
| 2026-08-21 | architecture | Settled the six open points of ADR 014 and amended it; stays Draft, ready for Implementing | ADR 014 | completed | development | [2026-08-21-architecture-1_handoff.md](2026-08-21-architecture-1_handoff.md) |
| 2026-08-21 | architecture | Settled that the final process-specific step of the ADR-0083 scenarios stays outside the core | ADR 015 | completed | development | [2026-08-21-architecture-2_handoff.md](2026-08-21-architecture-2_handoff.md) |
| 2026-08-21 | documentation | Split the example walkthroughs out of `README.md` into `examples/` | — | completed | docs/readme-examples-split | [2026-08-21-documentation-1_handoff.md](2026-08-21-documentation-1_handoff.md) |
| 2026-08-21 | investigation | Recorded the support-intake use case and measured it against the components that exist | ADR 013, ADR 014, ADR 016 | completed | docs/support-intake-scenario-note | [2026-08-21-investigation-1_handoff.md](2026-08-21-investigation-1_handoff.md) |
| 2026-08-21 | investigation | Read the interactive surfaces from the answerer's seat: the block never states the answer's form | ADR 013 | completed | development | [2026-08-21-investigation-2_handoff.md](2026-08-21-investigation-2_handoff.md) |
| 2026-08-22 | architecture | Diagnosed ADR 013 §6 as a wrong decision and opened Draft ADR 019 | ADR 013, ADR 019 | completed | development | [2026-08-22-architecture-1_handoff.md](2026-08-22-architecture-1_handoff.md) |
| 2026-08-23 | architecture | Stated the purpose and the documentation system, then, resumed 2026-08-24, decided the twelve gaps, the wrong-path diagnosis, the notes triage and the roadmap order | ADR 014, ADR 019 | completed | development | [2026-08-23-architecture-1_handoff.md](2026-08-23-architecture-1_handoff.md) |
| 2026-08-23 | documentation | Put the consumer into the ADR gate, admitted scenarios and a roadmap, and rewrote the registries to one-sentence rows split by phase | — | completed | docs/documentation-system | [2026-08-23-documentation-1_handoff.md](2026-08-23-documentation-1_handoff.md) |
| 2026-08-23 | documentation | Wrote the first class 2 scenario, `repository-interview`, with its six open decisions | — | completed | docs/repository-interview-scenario | [2026-08-23-documentation-2_handoff.md](2026-08-23-documentation-2_handoff.md) |
| 2026-08-23 | documentation | Gave the three shipped example walkthroughs their class 4 scenario headers and registry rows | — | completed | docs/class-4-scenario-rows | [2026-08-23-documentation-3_handoff.md](2026-08-23-documentation-3_handoff.md) |
| 2026-08-24 | documentation | Wrote the class 2 scenario `workflow-authoring`: a universal cycle authoring any workflow node by node, validated without a run | — | completed | docs/workflow-authoring-scenario | [2026-08-24-documentation-1_handoff.md](2026-08-24-documentation-1_handoff.md) |
| 2026-08-24 | documentation | Wrote the class 2 exit scenario `load-test-triage`: a fully automatic load-test triage carrying the G4–G7 and G11 measurements as its open decisions | — | completed | docs/load-test-triage-scenario | [2026-08-24-documentation-2_handoff.md](2026-08-24-documentation-2_handoff.md) |
| 2026-08-24 | architecture | Narrowed Draft ADR 014 to a class 4 gate consumer, decoupled Draft ADR 019 with the three shared-mechanism guards, and moved the output-family ADR ahead of ADR 014 | ADR 014, ADR 019 | completed | development | [2026-08-24-architecture-1_handoff.md](2026-08-24-architecture-1_handoff.md) |
| 2026-08-24 | architecture | Opened Draft ADR 020, the output composition functions, from the operator's `result-file-composition` note: one ADR, three scenario-derived functions, templates substitute and never iterate | ADR 020 | completed | development | [2026-08-24-architecture-2_handoff.md](2026-08-24-architecture-2_handoff.md) |
| 2026-08-24 | implementation | Implemented ADR 020: the grouped-table, verbatim-text and template-rendering functions, with the definition directory recorded in the state and the inventory example writing a report a human can read | ADR 020 | completed | feature/adr_020-output-composition-functions | [2026-08-24-implementation-1_handoff.md](2026-08-24-implementation-1_handoff.md) |
| 2026-08-24 | investigation | Sized the ADR 014 implementation as four sessions on one branch, and split the node-record channel its audit needs into its own ADR to be decided and implemented first | ADR 014 | completed | development | [2026-08-24-investigation-1_handoff.md](2026-08-24-investigation-1_handoff.md) |
| 2026-08-24 | architecture | Opened Draft ADR 021, the node-record channel: every visit leaves an engine-written record in an append-only stream outside the state, read by `show-records`, with its own class 4 evidence | ADR 021 | completed | development | [2026-08-24-architecture-3_handoff.md](2026-08-24-architecture-3_handoff.md) |
| 2026-08-24 | implementation | Implemented ADR 021: a record per concluded node visit appended to `records.jsonl` outside the state, read back by `show-records`, with the walk of the inventory example as its class 4 evidence | ADR 021 | completed | feature/adr_021-node-record-channel | [2026-08-24-implementation-2_handoff.md](2026-08-24-implementation-2_handoff.md) |
| 2026-08-24 | implementation | Seated provider adapters as the fifth registration kind: the adapter contract with its error classes, the `fake` adapter, the `providers` configuration section and the help surface | ADR 014 | completed | feature/adr_014-llm-node-and-provider-adapter | [2026-08-24-implementation-3_handoff.md](2026-08-24-implementation-3_handoff.md) |
| 2026-08-24 | implementation | Built the `llm` action: prompt resolution, the call, the two reply formats, codec decoding shared with the ADR 013 answer binding, and the call audit in the ADR 021 record channel | ADR 014, ADR 021 | completed | feature/adr_014-llm-node-and-provider-adapter | [2026-08-24-implementation-4_handoff.md](2026-08-24-implementation-4_handoff.md) |
| 2026-08-24 | implementation | Delivered the provider-adapter package as an external module with one OpenAI-compatible adapter over the standard library, and settled from by-hand evidence how much of a wrapped reply `format: json` tolerates | ADR 005, ADR 014 | completed | feature/adr_014-llm-node-and-provider-adapter | [2026-08-24-implementation-5_handoff.md](2026-08-24-implementation-5_handoff.md) |
| 2026-08-25 | implementation | Added the `lmstudio` residency adapter as a subclass of the protocol one, exercising the provider seat and `finalize` against a real server for the first time | ADR 014 | completed | feature/adr_014-llm-node-and-provider-adapter | [2026-08-25-implementation-1_handoff.md](2026-08-25-implementation-1_handoff.md) |
| 2026-08-25 | implementation | Let the provider block declare what a model is loaded with, forwarded to the load endpoint unread, and made the server's refusal of an oversized prompt arrive as `context_overflow` | ADR 014 | completed | feature/adr_014-llm-node-and-provider-adapter | [2026-08-25-implementation-2_handoff.md](2026-08-25-implementation-2_handoff.md) |
| 2026-08-25 | implementation | Shipped the `described`, `tiered` and `chunked` variants of the inventory example with the generic bus components they need, and turned the adapter's load into a swap | ADR 014 | completed | feature/adr_014-llm-node-and-provider-adapter | [2026-08-25-implementation-3_handoff.md](2026-08-25-implementation-3_handoff.md) |
| 2026-08-25 | documentation | Carried the documentation of the model call into `README.md`, the overview and the inventory walkthrough, then merged the branch and froze ADR 014 | ADR 014 | completed | feature/adr_014-llm-node-and-provider-adapter | [2026-08-25-documentation-1_handoff.md](2026-08-25-documentation-1_handoff.md) |
