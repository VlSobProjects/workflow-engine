# The interview that creates a repository and its documents

- **Identifier:** `repository-interview`
- **Class:** `2`
- **Answerers:** one answerer for every step — an agent (a model with tools). The agent reads the
  published question block, decides whether its context already answers it, interviews the human when
  it does not, and answers the engine through `resume --answer`. The human talks only to the agent and
  never answers the engine directly.
- **Input data:** the intake requirements of the consuming project, the external `java-claude-ai`
  repository — its ADR 0072 (stage-1 intake contract), ADR 0080 (intake interview protocol) and
  ADR 0083 (questionnaire engine contract). They fix the document set and the spec fields the
  interview must produce; the topic graph derived from them is the workflow definition. The dialogue
  itself is live and is not prepared.
- **Expected paths:** the direct path when the agent's context answers the root question; the
  clarification loop under `need_more_data` when it does not; the branch per project type selected by
  the answer text; a return to an earlier topic when the human changes their mind; the restricted-offer
  strategy on the last remaining attempt; the continuation by a fresh agent after the answering
  agent's context is lost; walking away as a declared failure answer. Details in the body.
- **Ends with:** end of workflow with the repository and its documents existing on disk, verified by
  function guards, and the interview record exported as a deliverable; failure under
  `max_visits_exceeded`, under a declared failure answer code such as `interview_abandoned`, or under
  a guard name when a terminal check refuses; every question in between is an ordinary pause.
- **ADRs exercised:** ADR 011, ADR 013, ADR 015, ADR 016, ADR 017, ADR 018

## The consumer

The `java-claude-ai` loop starts every story with an intake interview: the agent and the operator
co-produce the documents that seed the first planning task of an autonomous development loop
(its ADR 0080). The quality of the whole loop depends on this step. This repository ships the base
interview workflow; the consumer extends it with its own registered functions, codecs or nodes —
project scaffolding, git provisioning, its file formats — through the external module path (ADR 005)
and runs it as a skill of its intake agent. The development loop the created repository feeds runs
outside the workflow and outside this scenario.

## The answerer model

The engine never knows the human exists. It publishes a question block; the agent answers it — from
its own context when the context suffices, from a dialogue with the human when it does not. How many
turns that dialogue takes is invisible to the engine; one node visit consumes one agent answer.

One flow serves both kinds of user. A developer who knows the stack and a non-technical user who
expects recommendations are not two profiles: the same human answers one question as the first and the
next as the second, so no guard reads "technicality" and no branch encodes it. The agent absorbs the
difference. Recommendations are owed to the developer too: an accepted stack the loop cannot implement
for lack of fresh model data is an intake failure, so the instruction text of the stack topics tells
the agent to recommend versions and alternatives, not only to record choices.

## Continuation with a fresh agent

The interview must survive the loss of the answering agent. An agent's session is wiped, or a
different agent takes over: the run stays paused at its question (ADR 013 §6 — a `resume` without an
answer re-presents and consumes nothing), and the new agent must be able to continue as if it had
conducted the interview itself. That requires handing it the whole semantic context — the questions
asked, the answers given, the decisions taken at the branches, the choices recorded — in the terms of
the interview, without exposing the engine's internal mechanics.

What exists: the read surfaces of ADR 018 (`show-state`, `list-parameters`, `show-parameter`,
`show-journal`) let a returning answerer pull the parameters and the trail, but they speak the
engine's language — node ids, guard results, ordinals — and the journal deliberately stores no
values, so the exchange itself exists only where the flow author accumulated it. Here the author
does: the interview record on the bus is both the continuation context and the payload of the final
documents. Whether that author-side accumulation is the contract, or the engine owes a semantic
transcript surface of its own, is open decision 6.

## The interview shape

- A topic is a bounded cycle of `ask` nodes. The agent leaves a topic when it has collected enough
  for the transition, and the definition — not code — decides which topics a branch visits: a parser
  is a local utility and skips the security topic; a web application does not.
- Routing rides on the answer text. The instruction names a closed list of decision words plus
  `need_more_data`; `equals` / `any_of` guards select the transition. A decision that travels as a
  declared value is surfaced by the node's post function (ADR 015) before the guards read it.
- A question re-asked in place is bounded by `max_attempts`; a loop that leaves a node and returns —
  the human changed their mind and the agent routes back to re-ask an earlier topic — is bounded by
  `max_visits` (ADR 017).
- At the terminal points the check is code, never the model: function guards verify what the agent
  claims — the project path exists (`is_output_exist_folder`), the build files exist, the build file
  contains the declared markers (open decision 5).

## The topics

Drawn from the consumer's ADR 0080 (rules 12–14, 19, 21–22) and ADR 0072 (stage-1 fields):

1. **Root** — what the human wants built; one question, `need_more_data` loop, branch on the answer:
   web application, library, parser, free text.
2. **Stack** — language, framework, versions; the agent recommends and records compatibility
   constraints.
3. **Libraries** — per-branch concerns raised by the agent: monitoring, persistence, testing.
4. **Security** — only on the branches whose topic set declares it.
5. **Domain evidence** — sample inputs, format constraints, acceptance signal, host-tool dependencies.
6. **Scaffold** — the agent creates the repository instance, the story branch and the document set as
   instructed; the engine verifies existence.
7. **Documents** — goal, requirements, stack notes, architecture, implementation rules; the spec
   fields of ADR 0072 (story key, project root, goal, interview summary, merge plan) accumulate on the
   parameter bus as the interview runs.

The exact node graph is not fixed here; the principle is: the agent walks freely inside a topic cycle,
and the transition between topics fires when the collected data says so.

## The demonstration ending in the core

The consumer's formats and protocols stay outside the core. The shipped example ends with what the
core alone can produce: the interview record accumulated by `collect_answer`, exported as a
deliverable (ADR 011), next to the repository the agent scaffolded and the engine verified. Asking
the agent to compose a final document — an architecture file written from the record — is the
natural last node, and the scenario requires the base write for it: a string parameter written into
a file is a core capability, not a consumer extension. A core whose only text rendering is
`dict_list_to_pretty_table` cannot end this interview — or any scenario whose product is a document:
open decision 4.

## Expected paths

1. **Direct.** The human's first answer carries everything ("a web application in Java"); the agent
   answers the root from context, the `web` branch is taken, the stack topic recommends and records,
   the remaining topics of the branch run, the scaffold is verified, the run ends.
2. **Clarification.** The root answer does not suffice; the agent answers `need_more_data`, the loop
   re-presents with the agent offering options, bounded by `max_attempts`.
3. **Restricted offer.** On the last remaining attempt the agent changes strategy: instead of a free
   question it offers only the few options its context supports. Requires the agent to know how many
   attempts remain: open decision 1.
4. **Return.** During the libraries topic the human revises the framework choice; the agent routes
   back to the stack topic; the re-entry counts against `max_visits`, and exhaustion fails the run
   under `max_visits_exceeded`.
5. **Fresh agent.** The interview pauses mid-way and the answering agent's context is gone — wiped or
   replaced. A new agent pulls the semantic context of the run, resumes the paused question and the
   interview continues; the human notices nothing.
6. **Walk-away.** The human stops answering reasonably or abandons; the agent sends the declared
   failure answer and the run fails under its code, `interview_abandoned`.

## Open decisions the scenario lacks

1. **The answerer cannot see the remaining bound.** The strategy change of path 3 needs the published
   block to carry attempts and visits remaining; today the ordinals are journaled on
   `interactive_answered` (ADR 017 §4) but the block says nothing, and pulling the journal for a bound
   is reading an audit trail as a contract. Touches ADR 013 §6 and the ADR 019 question document.
2. **The block never states the answer's form** (`2026-08-21-investigation-2`); an agent composing an
   answer needs the declaration, not prose. ADR 019 territory.
3. **A structured answer's keys are unchecked.** The stack topic binds a dict (language, framework,
   versions) and `type: dict` accepts any dictionary — gap G4 of `2026-08-23-architecture-1`.
4. **No base text write.** The core renders a table but cannot write a composed string into a file
   or artifact, so the final document of the demonstration ending is not yet expressible. The
   scenario requires the base capability — write a string parameter into a file — in the core; the
   wider document-artifact family (author-defined shapes, template-rendered documents) is gap G6 and
   is decided there.
5. **No content check for the terminal guard.** Existence checks exist
   (`is_output_exist_file` / `is_output_exist_folder`); "the build file contains the declared
   markers" has no core guard. Either a core file-content guard or a consumer-registered validator;
   decided when the example is built.
6. **The continuation context has no contract.** A fresh agent continues from what the author
   accumulated on the bus plus the ADR 018 surfaces, which expose the engine's mechanics, not the
   interview. Whether the author-side record is the contract, or the engine owes a semantic
   transcript surface, is the transcript question ADR 018 left open; it touches ADR 019 as well.
