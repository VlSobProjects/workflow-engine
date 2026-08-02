# ADR 003: The boundary between persistence and the working directory

## Status
Draft

## Active branch
None

## Context

A run of a workflow needs two different things kept somewhere.

- The **workflow definition and the run state**. These are data. They are written at every turn so
  that a run can be resumed, and they are the only things the engine itself needs to continue.
- The **files a run produces**. Artifacts, copies, generated documents. These are the point of many
  workflows and they are consumed by tools that expect a real path on a real disk.

Today both are held by one object. `Storage` is an abstract class over `StateSource` and
`WorkflowSource`, and `JsonStorage` is its only implementation. The intention was already that the
medium is replaceable; a backend over a database is planned. The abstraction does not yet support
that, and the reason is that the two things above are not separated.

Where the current code prevents a second backend:

- `Storage.__init__` takes a `working_dir: Path`. Every backend, including one over a database, has
  to accept a directory.
- `WorkflowSource.upload_workflow` and `Storage.start_workflow` take a `Path` in the abstract
  signature, so the source of a definition is a file at the level of the contract.
- `StateModel` has no serialization of its own. `json_storage` reads `state.__dict__` directly and
  rebuilds the state through a JSON `object_hook`. The knowledge of the shape of the state lives in
  the backend, so a second backend has to restate it. That decoding is also the source of a defect
  found while reviewing ADR 002: the hook runs over every nested dictionary, so a node whose
  identifier matches a state field, such as `params` or `guard_results`, makes a saved state
  impossible to load.
- `start_workflow` writes `self.working_dir` into `state.work_dir`, so the place where the state is
  stored and the place where the run produces files are by construction the same place.

## Decision

Persistence and the working directory are two separate concepts, and the engine depends on both
separately.

**Persistence** is an abstract contract that carries no assumption about the medium. It moves data,
not files.

- `StateModel` and `WorkflowModel` own their own conversion to and from a plain dictionary. A backend
  moves dictionaries and does not know their shape.
- No signature in the contract mentions a filesystem path. A definition supplied from outside is
  handed to the engine as data; reading it from a file is the job of whoever calls the engine, or of
  a helper that belongs to the file based backend.
- A concrete backend is free to require whatever it needs in its own constructor. The file based
  backend takes a directory; a database backend takes a connection. That belongs to the backend, not
  to the contract.

**The working directory** is a real directory on a real disk, and stays one. It is where a run
produces files, and it is deliberately not stored in the persistence backend: putting generated files
into a database is possible but impractical, and the tools that consume them expect paths.

- The working directory is given to a run, not to the persistence backend.
- It stays in the state, because a resumed run has to find its own files again. It is recorded there
  as the identity of a workspace, not as the location of the state.
- A file based backend may keep the state inside the same directory. That is its own choice and not
  part of the contract.

## Alternatives considered

### A. Keep the path in the contract and let other backends emulate it
A database backend maps identifiers onto pseudo paths.
Cheapest today and no change to existing code. Rejected because every backend then has to pretend to
be a filesystem, and the pretence leaks: the state decoder already checks the working directory with
`is_dir()`, so a backend that has no directory fails on load rather than at configuration.

### B. Put everything, including the produced files, into the backend
One place for everything, uniform and simple to reason about.
Rejected. Generated files are the purpose of many workflows and are consumed by tools that expect a
path. Streaming them through a database costs more and buys nothing, and the engine would have to
materialise them on disk anyway before any external tool could use them.

### C. Keep one object but split its interface into two
`Storage` continues to exist and exposes both a persistence part and a workspace part.
Rejected because it preserves exactly the coupling that has to go: a database backend would still be
required to supply a workspace it has nothing to do with.

### D. Separate persistence from the working directory
Chosen. The engine asks for state and definition from one collaborator and for a workspace from
another. Each backend then implements only what it is about. The cost is that the caller now supplies
two things instead of one, and that both models gain explicit serialization.

## Consequences

- A second backend becomes a matter of moving dictionaries, which is a low bar.
- Explicit `to_dict` and `from_dict` on the models remove the JSON `object_hook`, and with it the
  class of defect where a node named after a state field makes a saved state unloadable.
- The shape of the state is defined in one place, so a change to it is a change to one file rather
  than to every backend.
- The caller of the engine supplies both a persistence backend and a working directory. That is more
  than it supplies today.
- Existing callers and the file based backend change. The stored format does not have to change.
- The state is written on every turn. For a file based backend that is a file rewrite; for a database
  backend it is a transaction per node. This decision does not address how often the state is
  written, and a backend that finds the frequency expensive will have to raise it as its own
  decision.
- Nothing here says the working directory has to be local in the long run. It says it is not the
  concern of the persistence backend. A remote or virtual workspace remains a later decision.

## Related ADRs

- ADR 002 node composition. The decoding defect that this decision removes was found while reviewing
  its implementation.
- ADR 001 exception architecture. Failures raised while decoding a state or a definition belong to
  its hierarchy, and this decision moves where that decoding happens.
- How data passes between nodes is not decided here, but it determines what has to be serialized.

## Implementation notes

Not started. This decision may not enter implementation while ADR 002 is still open.

Open points to settle when it does:

- Whether the workflow definition is still saved by the engine at all, or is supplied on every call.
  Today `upload_workflow` copies the definition into the storage directory.
- Whether `work_dir` keeps its current name in the state once it no longer implies where the state
  lives.
- Whether the file based backend keeps its current file names and layout, so that existing runs
  remain readable.

## Change log

- Draft created. Option D chosen after comparing it with emulating a filesystem in every backend,
  storing produced files in the backend, and splitting the interface without splitting the object.
  The working directory was confirmed as a deliberate design choice rather than a leak.
