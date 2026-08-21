# The instruction that lets an agent drive any workflow without being told what it is

- **Date:** 2026-08-21
- **Trigger:** discussion in session `2026-08-21-investigation-1`. The intended way to put the engine
  in someone's hands: they install it, hand an agent one instruction, and the agent walks whatever
  workflow it is pointed at to the end. The instruction carries no scenario — all the specifics live
  inside the workflow definition — and its stated destination is a Skill.
- **Status:** open
- **Affected:** ADR 007 (CLI contract — the commands the agent drives), ADR 009 (help surfaces —
  component discovery), ADR 013 (the published question block is what the agent reads),
  ADR 016 (what the question can carry inside its text), ADR 018 (read surfaces — how a returning
  agent catches up), `documentation-rules.md` §1 (the map does not admit this document),
  `2026-08-19-installation-and-distribution.md` (the engine has no delivery channel, and a Skill is
  one), `2026-08-20-question-rendering-for-an-audience.md` (who the published text is written for)

## What is being proposed

One document, shipped with the engine, that an agent is given once. From it the agent knows how to
start a run, how to recognize that the run is waiting for it, how to compose an answer, what to do
when it cannot answer, how to know the run has ended and how to fetch what the run produced. It knows
none of that about *this* workflow in particular — it learns the specifics from the run itself.

The constraint that it carries no scenario is the interesting part. It is not a style preference: it
is what makes one instruction serve every workflow, and it is what turns the document into a Skill
later rather than into a per-customer prompt.

## Why the constraint is also a measurement

If the instruction may not mention the scenario, then everything the agent needs in order to act has
to arrive from the engine's own surfaces: the published `question` block and the result of the
command. Writing the instruction is therefore a test of whether those surfaces are self-sufficient,
and the places where the author reaches for scenario knowledge are exactly the gaps.

What is already in place for that test:

- The exchange contract is published per question — the node, the instruction text, the options, the
  declared `answer` names and types, the error catalogue and the generic code (ADR 013).
- Values reach the agent inside the sentence rather than beside it (ADR 016), so a question is
  readable without knowing which parameters exist.
- The outcome is unambiguous at the transport: exit `0` success, `2` paused, `3` failed workflow, `4`
  command-level error (`README.md`, "Exit codes").
- The answer document has a fixed shape, including how a refusal is expressed (`README.md`,
  "Answering an interactive workflow").
- A returning agent can read the run's state and journal through the ADR 018 commands.

What the instruction will have to answer, and where the answer is not obvious today:

1. **When is the agent allowed to refuse, and what does refusing cost?** A declared error code routes
   the run somewhere the author chose; the generic `answer_failed` usually fails the node. An agent
   that refuses because it is unsure is making a routing decision it cannot see the consequences of.
2. **What does the agent do with a re-ask?** A wrong answer text can send the run back to the same
   node, and attempts are bounded. Nothing in the published block tells the agent how many attempts
   remain, so "try again differently" is advice the agent cannot cost.
3. **How does the agent know the shape it must return?** `answer` declares names and types; for a
   `dict` or a `list` the required internal shape lives in the wording of the question. This is the
   same finding as gap 4 of `2026-08-21-support-intake-use-case.md`, arriving from the agent's side.
4. **What may the agent read on its own initiative?** The read surfaces exist, but an instruction that
   tells an agent to inspect the state before answering is teaching it to depend on the bus rather
   than on the question — the opposite of what the published boundary was for.
5. **What the instruction must not restate.** `README.md` already carries the answer document, the
   refusal rules, the exit codes and the binding of inputs. Copying them into the instruction breaks
   `documentation-rules.md` §3, so the instruction has to be the *loop and the judgment* — what an
   agent does in what order and how it decides — and link for the contract. That boundary is easy to
   state and hard to hold, and it is the main risk to the document's quality.

## The map does not admit this document

`documentation-rules.md` §1 is a closed map, and nothing in it fits. In particular it is **not**
`AGENTS.md`: that file addresses an agent working *on this repository*, and this one addresses an
agent *using the engine*. They have opposite audiences, and merging them would be the worst available
outcome — a contributor's routing document that also tells a stranger's agent how to answer a
question.

The options, none of them free:

- **Inside `examples/`.** Cheapest, and wrong by the map's own words: that entry is the shipped
  templates, their registry and one walkthrough each. The instruction is not a walkthrough of
  anything.
- **A root document.** The root is deliberately thin — `README.md` plus the three entrypoints — and a
  fourth root file has to earn a map row of its own.
- **A new mapped location shaped as the Skill it is meant to become.** Most honest about the intent,
  and the most expensive: it introduces a directory whose format belongs to a third party.

## The Skill is not recorded anywhere yet

The word does not appear in `README.md` or anywhere under `docs/`. This note is its first record in
the repository, which is worth stating plainly: the plan existed in conversation, not in the project.

Two consequences worth weighing before a Skill is built rather than after. First, its format is owned
by someone else, so the repository would carry a document whose shape it does not control — the same
class of dependency as adding a library, and it deserves the same justification. Second,
`2026-08-19-installation-and-distribution.md` records that the engine has no delivery channel at all:
the wheel installs and runs, but ships nowhere, carries no examples, states no licence and reports no
version. A Skill is a delivery channel for the instruction, and building it before the engine itself
can be obtained is putting the roof on before the walls. The plain document should exist first and be
proven by use; promoting it to a Skill is a second, separate decision.

## What the session that writes it has to decide

1. **Where it lives, and the map row that admits it** — one of the three options above, taken
   deliberately rather than by dropping a file next to the others.
2. **Whether it is one document or two.** The user installing the engine and the agent being
   instructed are different readers with different needs; `README.md` may already be the first
   reader's document, in which case only the second is new.
3. **What it is allowed to assume about the agent.** An instruction written for a capable model and
   one written for a small one are different documents; the rendering question in
   `2026-08-20-question-rendering-for-an-audience.md` is the same question one level down.
4. **How it is proven.** It should be exercised against the interactive templates that exist rather
   than reasoned about — `approve-and-copy` today, and whatever `examples/` gains next — with the
   places where the agent had to be told something scenario-specific recorded as gaps, not patched
   into the instruction.
