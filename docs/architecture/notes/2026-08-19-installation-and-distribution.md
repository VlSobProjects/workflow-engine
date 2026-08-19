# How the engine is installed on Windows, macOS and Linux

- **Date:** 2026-08-19
- **Trigger:** the README precondition added in session `2026-08-19-documentation-5` (audit finding 5):
  stating what `workflow-engine` needs before it runs exposed that the project has no answer for how
  an operator obtains the command in the first place
- **Status:** open
- **Affected:** ADR 005, ADR 007, ADR 008

## What is already true

Packaging is not the gap. `pyproject.toml` builds a wheel with hatchling and declares the console
script `workflow-engine`; `tests/test_install_smoke.py` builds that wheel, installs it into a fresh
virtual environment and runs the CLI from it. A `pip install` of the built artifact works.

The code is operating-system neutral by construction: `src/` contains no branch on `os.name` or
`sys.platform`, paths go through `pathlib`, the user configuration directory comes from
`platformdirs`, and stored paths are POSIX regardless of host (ADR 008). The only platform branch in
the repository is in the smoke test, choosing `Scripts/` or `bin/` for the launcher.

## What is missing

1. **No delivery channel.** The repository is private, so `uv tool install git+<url>` and
   `pipx install git+<url>` work only for someone who already has access. On PyPI the name
   `workflow-engine` is taken by an unrelated package (0.1.0, November 2023), so publishing would
   require a different distribution name. The import package `workflow_engine` could keep its name,
   at the cost of the two no longer matching.
2. **No evidence for macOS and Linux.** There is no CI: `.github/` holds only
   `copilot-instructions.md`. Every test run so far happened on Windows 11. Nothing suggests the other
   two platforms break; nothing proves they do not.
3. **The README describes one route only** — a clone with `uv sync` — because that is the only route
   that has ever been exercised.

## Options, and what each costs

- **CI matrix** (ubuntu, macos, windows: `pytest` plus the wheel smoke test). Converts "should work"
  into evidence, and would catch path, encoding and launcher differences before a release. Costs one
  workflow file, but introduces continuous integration to a project that has deliberately had none, so
  it is a process decision, not only a file.
- **An install section in the README** describing exactly the routes that work today, per platform:
  clone with `uv sync`, `uv tool install <path-to-clone>`, or installing the built wheel. Cheap and
  honest, but it does not solve delivery to anyone outside the repository.
- **Publishing to PyPI.** Gives `uv tool install <name>` and `pipx install <name>` anywhere. Requires
  choosing a distribution name, an account with trusted publishing, a release procedure, and a
  commitment to versioning. A published name and version cannot be taken back.
- **Deciding not to distribute during phase 1** and stating that the engine is used from a clone. The
  question then returns the first time the engine is handed to someone else.

## Open questions

1. Which distribution name, given that `workflow-engine` is taken on PyPI, and whether the import
   package follows it or diverges from it.
2. Which platforms the project actually claims to support, and what evidence backs the claim. A
   supported platform without a CI run is a claim, not a fact.
3. Whether the private repository stays private, since that alone decides whether a git-URL install is
   available to anyone but the owner.
4. Whether a release procedure (tag, build, publish, changelog) belongs to `docs/processes/` next to
   the git workflow, or is part of the same decision.

A decision here is the natural moment to also settle what "supported platform" obliges the project to
run, which is why the CI question is inside this note rather than treated as tooling housekeeping.

## Smaller thing this surfaced

`README.md` lists `%LOCALAPPDATA%` on Windows and `~/.config` on Linux as the user configuration
directory, and omits macOS, where `platformdirs.user_config_dir()` returns
`~/Library/Application Support`. That is a documentation fix, not part of this question, but it comes
from the same blind spot.
