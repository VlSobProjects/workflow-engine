# Deferred architectural questions from ADR 012 implementation

- **Date:** 2026-08-18
- **Trigger:** observations surfaced while implementing ADR 012 (workflow input parameters).
- **Status:** open
- **Affected:** ADR 006 (data flow, codec contract), ADR 009 (help contract), ADR 011 (deliverables),
  ADR 012 (inputs), ADR 014 (Draft, decides §1 for prompt templates; §3 waits for its own ADR after
  ADR 013 — session `2026-08-19-architecture-1`), ADR 013 (Accepted; §3 was not a prerequisite for it —
  session `2026-08-19-architecture-2`; §4 was found while fixing its text rendering — session
  `2026-08-19-implementation-14`),
  ADR 018 (session read surfaces — removes the `inputs` field of `show-state`, sharpening the missing
  workflow-definition introspection surface; Accepted 2026-08-21, publishing the full codec name on two
  new read surfaces — see §2)

Four model choices that outlive the ADR 012 session and are not decisions yet. The facts behind them
are recorded in the ADR 012 change log; this note carries only the open questions a frozen ADR cannot
hold. None blocks anything.

## 1. Reference resolution is shallow

`param.<name>` / `output.<name>` / `artifact.<name>` resolve only at the top level of a node's function
parameters, not inside nested list/dict values (see the ADR 012 change log on the example seeding
restructure).

Question: keep resolution shallow and make "references only at the top level" an explicit operator rule,
or introduce deep resolution that recurses into containers? Deep resolution costs ambiguity (a literal
string that looks like a reference), performance, and a recursion boundary. Touches ADR 006.

Narrowed in session `2026-08-20-architecture-3`: ADR 016 (Draft) resolves references *inside text* for
fields declared as template text, which covers the in-sentence case ADR 014 open point 1 was waiting
for. Whole-value resolution stays shallow everywhere; the deep-resolution branch of this question
remains open on its own merits.

## 2. Codec full names are Python-version dependent

The stored full codec name is version-specific (`pathlib._local.Path` on 3.13); reload survives only via
the bare-name fallback (see the ADR 012 change log).

Question: should the codec registry own stable public aliases (always `pathlib.Path`, `builtins.int`)
decoupled from `__module__`, so persisted definitions and the help contract are portable across
interpreter versions? Touches the ADR 006 codec round-trip and the ADR 009 help contract. (Hardening,
low urgency.)

Widened by ADR 018 (session `2026-08-21-implementation-1`): the full codec name is now contract on two
read surfaces — the `type` field of `list-parameters` and the `object_type` of the `show-parameter`
envelope — where before it reached the outside only through `state.json`. Every new publisher raises
the price of a later rename, so the urgency is no longer low.

Direction under discussion (2026-08-21): the registry keys each codec by one stable short name
(`Path`, `int`) and keeps the full names as synonyms. An interpreter transition adds the new spelling
as one more synonym instead of replacing the old one, so definitions and states persisted under an
older interpreter keep resolving — backward compatibility by accretion. The published surfaces carry
only the short name; the synonyms exist for resolution — persisted state and machine readers — not
for publishing. For the core codecs that already exist this promotes the bare-name fallback from a
fallback to the contract. Open edges: whether the `object_type` of the persisted envelope changes its
spelling, which is a state-migration question; and how an external module claims a short name without
colliding with the core, which touches the entry-point discovery note
(`2026-08-19-entry-point-discovery.md`).

## 3. No introspection surface for the workflow definition

ADR 012 §1 says `inputs` "surfaces through the CLI result data and the ADR 009 help contract", but the
implementation surfaces `inputs` and `deliverables` only in `run`/`resume`/`show-state` result data;
neither appears in `help-components`/`help-component`, which describe component *types*, not a specific
workflow's definition. The §1 wording is thus unreconciled with what was built.

Question: is result-data enough, or should there be a definition-introspection surface — a
`describe-workflow` command, or extending the help contract to workflow-definition surfaces — so tooling
can read what a workflow needs and produces without running it? Touches ADR 009, ADR 011 and ADR 012; if
pursued, reconcile the ADR 012 §1 wording (a frozen ADR is edited only under supersession or an editorial
correction).

Settled in `2026-08-19-architecture-2`, against the open question the previous architecture session
left: this is **not** a prerequisite for ADR 013. An agent driving a paused run receives the answer
declaration inside the presentation, so it never has to read the workflow definition to answer. The
question stays open on its own merits — an agent choosing *which* workflow to run still has nothing to
read — and remains its own ADR when its turn comes.
## 4. The string transport decodes JSON escapes in a quoted value

Found while fixing the text-rendering rule (session `2026-08-19-implementation-14`), and documented in
the README rather than changed, because the rule it follows is in a frozen ADR.

A typed `--input` value is parsed as JSON with a fall back to the raw string (ADR 012 §"binding rule").
A bare Windows path falls back and binds intact. A value that carries its own quotes does not fall
back: `p:Path="C:\tmp\file.txt"` is a valid JSON string, so `\t` becomes a tab and `\f` a form feed,
and the input binds silently as a different path. Nothing is malformed from the transport's point of
view, so nothing can be reported.

Question: should the JSON parse be reserved for the codecs that need it — collections and objects —
while a scalar codec binds the raw string? That would make the quoted form harmless and remove the one
place where the transport can change a value without saying so. It contradicts the ADR 012 wording,
which applies the rule to every typed value, so it is a supersession or an editorial correction of a
frozen ADR, not an implementation choice. Touches ADR 012 and, through the answer document, ADR 013 —
there the values arrive as real JSON, where a backslash is escaped by the format itself.

