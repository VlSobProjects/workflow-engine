# Deferred architectural questions from ADR 012 implementation

- **Date:** 2026-08-18
- **Trigger:** observations surfaced while implementing ADR 012 (workflow input parameters).
- **Status:** open
- **Affected:** ADR 006 (data flow, codec contract), ADR 009 (help contract), ADR 011 (deliverables),
  ADR 012 (inputs), ADR 014 (Draft, decides §1 for prompt templates; §3 waits for its own ADR after
  ADR 013 — session `2026-08-19-architecture-1`), ADR 013 (Implementing; §3 is not a prerequisite for
  it — session `2026-08-19-architecture-2`)

Three model choices that outlive the ADR 012 session and are not decisions yet. The facts behind them
are recorded in the ADR 012 change log; this note carries only the open questions a frozen ADR cannot
hold. None blocks anything.

## 1. Reference resolution is shallow

`param.<name>` / `output.<name>` / `artifact.<name>` resolve only at the top level of a node's function
parameters, not inside nested list/dict values (see the ADR 012 change log on the example seeding
restructure).

Question: keep resolution shallow and make "references only at the top level" an explicit operator rule,
or introduce deep resolution that recurses into containers? Deep resolution costs ambiguity (a literal
string that looks like a reference), performance, and a recursion boundary. Touches ADR 006.

## 2. Codec full names are Python-version dependent

The stored full codec name is version-specific (`pathlib._local.Path` on 3.13); reload survives only via
the bare-name fallback (see the ADR 012 change log).

Question: should the codec registry own stable public aliases (always `pathlib.Path`, `builtins.int`)
decoupled from `__module__`, so persisted definitions and the help contract are portable across
interpreter versions? Touches the ADR 006 codec round-trip and the ADR 009 help contract. (Hardening,
low urgency.)

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
