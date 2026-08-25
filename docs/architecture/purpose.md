# Purpose

This document states what the engine is for. Every architecture discussion starts by reading it.

## What the engine is for

Run a complex technical task as a graph of precisely specified subtasks. Deterministic work is
done by registered functions; judgment is done by language models, each step by the smallest
model that can do it. Which node runs next is decided at run time from the data the previous
nodes produced, and is not known in advance.

## The method

The author decomposes the task. Every subtask declares what it produces, and the engine checks
the result at the boundary with code (guards), never with a model. A model step receives only
what its subtask declares and nothing else: the limit is enforced by the engine, not by the
model's discipline. Deterministic steps use no model; a small local model is preferred to a
large one; a large one is used where a decision depends on accumulated evidence. The method
lives in the workflow definition, a file that is reviewed, versioned and shared.

A situation the author did not foresee is a foreseen exit: the run ends with a handover to a
human that carries the collected evidence and states why the flow stopped. The engine never
invents a step.

## Why not one agent with tools and prompts

A prompt handed to an agent is not automation: somebody sits and watches what the agent does.
Given the whole task in one context, a model loses the instructions under the data: it decides
about what it has not seen, and the same task takes a different path every time. Splitting the
task into narrow steps by hand is the same method done without a tool.

Many steps need no model at all. A pipeline of checks — the key endpoints answer, every service
runs the expected version, the logs carry no deployment failure — gives the answer before a model
is called, and often instead of it.

Here the split is an artifact, the limit of each step is enforced, the checks are code, and every
model answer is recorded, so a run can be explained and repeated.

## What makes this engine different

It is a process the caller walks from outside: a command-line engine with persisted, resumable
sessions and a journal. Whoever answers a step — a human, an external agent, or a model the
engine calls — answers through one contract. The engine is not a library an agent is embedded in.

## Boundaries

- No planning: the engine runs the graph the author wrote.
- No chat or agent framework, no scheduler, no user interface.
- Parallel execution of nodes is outside the current scope. The first answer to a slow step is
  concurrency inside a function; fork/join of nodes is a decision taken only on a serious
  external request.
- Several workflows run as several processes in separate directories; the engine protects a
  session from concurrent access and promises nothing beyond that.

## Origin

Load-testing analysis of a system with complex business logic: large volumes of logs, metrics
and test reports; problems that range from unrealistic test scenarios and miscalibrated load to
real defects in indexing, queues and scaling; and a direction of investigation that depends on
what the previous step found. Deterministic steps fetch and filter, small models aggregate what
is known only at run time, large models decide the next step, and a human receives the handover.

## What counts as done

A scenario of that shape — fetch, aggregate, decide, branch, hand over — runs end to end on
prepared data with a local model; its path is determined by the data and explained by the
journal; and an author who knows the domain but not the engine can produce it. The documentation
alone is the floor of that authoring claim; its proof is assisted authoring, where a workflow the
engine runs asks, validates and assembles and the author brings only the intent. The two halves gate two
phases of the roadmap: the run closes the earlier, the authoring the later.

A run against a live system under test is the gate for publication, not for this condition.
