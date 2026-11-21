# How the engine is installed on Windows, macOS and Linux

- **Date:** 2026-08-19
- **Trigger:** the README precondition added in session `2026-08-19-documentation-5` (audit finding 5):
  stating what `workflow-engine` needs before it runs exposed that the project has no answer for how
  an operator obtains the command in the first place; extended 2026-08-19 after a manual dry run of
  "what would a Windows operator do from zero", taken before cutting a first GitHub release
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

A manual dry run on Windows 11 on 2026-08-19 went further than that test, which only calls
`help-components` from the installed launcher. `uv build` produced both artifacts
(`workflow_engine-0.1.0-py3-none-any.whl`, 94 KB; `workflow_engine-0.1.0.tar.gz`, 264 KB); the wheel
installed into a fresh virtual environment outside the clone, pulling `platformdirs`, `prettytable`
and `wcwidth`; and `run --workflow-file folder-inventory-to-csv.json --input "scan_root:Path=…"
--export-dir out` completed with exit code `0` and the exported CSV. `uv tool install <wheel>` into an
isolated tool directory produced a working launcher the same way. So an operator route that never
touches the repository exists in practice, not only in principle — it is undocumented, not absent.

That run also fixes what the operator has to install first. With `uv`, nothing else: uv downloads the
managed Python 3.13 itself, so `uv` is the single prerequisite. Without uv the operator must first
obtain Python 3.13 and then `pipx`, which is two acquisitions instead of one, both of which the
project would have to describe per platform.

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
4. **The wheel carries no workflows.** `[tool.hatch.build.targets.wheel]` packages `src/workflow_engine`
   and nothing else, so the built wheel holds 72 entries, none of them under `examples/`. Every command
   in the README's "Running the examples" section names a file from `examples/`, which an operator who
   installed the wheel does not have. The one route that reaches a non-cloner therefore delivers an
   engine with no input to run it on, and the documented first steps are unreachable from it. Whether
   examples are packaged data, a separate artifact, or something the operator is expected to author is
   a distribution decision, not a packaging detail.
5. **Nothing says which build an operator is holding.** There is no `--version`: the flag is not
   declared, so `workflow-engine --version` exits `4` with the usage text. Once artifacts leave the
   machine that built them, the version in `pyproject.toml` is invisible to the person running the
   command, and a bug report cannot name the build it came from.
6. **The sdist ships the project, not the product.** Its 214 entries include `docs/` (100 files),
   `tests/`, `AGENTS.md` and `CLAUDE.md` — the working rules of this repository, handed to whoever
   downloads it. That is defensible for an internal artifact and a decision worth making consciously
   for a public one.
7. **No licence.** The repository has no `LICENSE` file, so every artifact discussed here is delivered
   with no stated terms of use. This blocks any channel that hands the engine to a third party,
   independently of which channel is chosen.
   Settled 2026-11-21: the repository carries the MIT licence in `LICENSE`, declared in
   `pyproject.toml` (session `2026-11-21-documentation-1`).

## Options, and what each costs

- **CI matrix** (ubuntu, macos, windows: `pytest` plus the wheel smoke test). Converts "should work"
  into evidence, and would catch path, encoding and launcher differences before a release. Costs one
  workflow file, but introduces continuous integration to a project that has deliberately had none, so
  it is a process decision, not only a file.
- **An install section in the README** describing exactly the routes that work today, per platform:
  clone with `uv sync`, `uv tool install <path-to-clone>`, or installing the built wheel. Cheap and
  honest, but it does not solve delivery to anyone outside the repository.
- **A GitHub release carrying the built artifacts.** The wheel and the sdist are attached to a tag, and
  the operator installs with `uv tool install <downloaded wheel>` — the route verified above. It needs
  no distribution name, reserves nothing irrevocably, and turns into a public channel the moment the
  repository opens, without any change to how it is produced. While the repository is private the
  download itself needs credentials (`gh release download`, or a browser session), so it delivers to
  people who already have access — the same limit as a git-URL install, but with an artifact that is
  built once instead of per install. It also forces the questions a release procedure answers: what the
  assets are, where the version number comes from, and what the release notes say.
- **Publishing to PyPI.** Gives `uv tool install <name>` and `pipx install <name>` anywhere. Requires
  choosing a distribution name, an account with trusted publishing, a release procedure, and a
  commitment to versioning. A published name and version cannot be taken back.
- **A frozen executable** (PyInstaller or equivalent), so the operator needs neither uv nor Python. It
  is the only option that removes the Python prerequisite entirely, and the most expensive one: a new
  build dependency, a build per platform — which cannot be produced without the CI matrix above — a
  binary two orders of magnitude larger than the wheel, and an artifact whose contents are opaque to
  antivirus and to the operator alike. It also puts `external_modules` in question: a frozen
  interpreter resolves imports against the bundle, and whether it still finds a plugin module that
  merely sits on the operator's `PYTHONPATH` would have to be verified, not assumed — the plugin
  mechanism ADR 005 rests on is exactly what the operator needs the command for.
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
5. What an operator receives besides the engine. The wheel alone cannot run the documented quickstart,
   so either the examples travel with it (packaged data, plus a way to get them out of the installed
   package onto disk), or they travel beside it (a second release asset), or the README stops treating
   them as the first thing an operator does.
6. Where the version number lives. `pyproject.toml` hardcodes `0.1.0` and the tag `v0.1.0` already
   exists, so the two are coupled by hand and can already disagree. Whether the tag derives the
   metadata, the metadata governs the tag, or a release simply refuses to build when they diverge, is
   part of the release procedure, and the answer decides whether a `--version` flag can be trusted.
7. What the licence is, which cannot be deferred past the first artifact handed to anyone. Settled 2026-11-21:
   MIT.

A decision here is the natural moment to also settle what "supported platform" obliges the project to
run, which is why the CI question is inside this note rather than treated as tooling housekeeping.

## Smaller things this surfaced

A missing `--version` flag (point 5 above) is a CLI gap, not an architectural one, but it only becomes
visible when the artifact travels; it is recorded here because the release is what makes it matter.

`README.md` lists `%LOCALAPPDATA%` on Windows and `~/.config` on Linux as the user configuration
directory, and omits macOS, where `platformdirs.user_config_dir()` returns
`~/Library/Application Support`. That is a documentation fix, not part of this question, but it comes
from the same blind spot.
