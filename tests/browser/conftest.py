"""Reports of real runs of shipped examples, written once for the browser suite. See ADR 022.

The suite needs the `browser` dependency group; where Playwright is not installed it is not collected
at all, so a fresh clone and the default `uv run pytest` never see it.
"""

import contextlib
import importlib.util
import io
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main

if importlib.util.find_spec("playwright") is None:
    collect_ignore_glob = ["test_*.py"]

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
INVENTORY = EXAMPLES_DIR / "folder-inventory-to-csv.json"
APPROVE_AND_COPY = EXAMPLES_DIR / "approve-and-copy.json"
BUDGET = 14


@dataclass(frozen=True)
class Report:
    """One written report: the file a browser opens and the session it tells."""

    path: Path
    session_id: str

    @property
    def url(self) -> str:
        return self.path.as_uri()


def cli(argv: list[str]) -> tuple[int, dict[str, object]]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(out.getvalue()))


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.config = root / "workflow_engine_config.json"
        self.config.write_text(
            json.dumps({"work_dir": (root / "runtime").as_posix(), "external_modules": [], "storage": {}})
        )

    def run(self, argv: list[str]) -> tuple[int, dict[str, object]]:
        return cli([*argv, "--config", self.config.as_posix()])

    def start(self, workflow: Path, *inputs: str) -> tuple[int, str]:
        argv = ["run", "--workflow-file", workflow.as_posix()]
        for assignment in inputs:
            argv += ["--input", assignment]
        code, response = self.run(argv)
        return code, cast(str, response["session_id"])

    def report(self, session_id: str) -> Report:
        code, response = self.run(["report", "--session-id", session_id])
        assert code == 0, response
        data = cast(dict[str, object], response["data"])
        return Report(Path(cast(str, data["path"])), session_id)


def create_tree(root: Path) -> Path:
    """Two files in the root and one in a nested folder, so the walk loops and recurses."""
    (root / "nested").mkdir(parents=True)
    (root / "first.txt").write_text("first")
    (root / "second.txt").write_text("second")
    (root / "nested" / "third.txt").write_text("third")
    return root


@pytest.fixture(scope="session")
def reports(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Report]]:
    """The four agreed cases: completed with a loop, failed, paused on the budget, paused at a question."""
    root = tmp_path_factory.mktemp("reports")
    space = Workspace(root)
    written: dict[str, Report] = {}

    code, session_id = space.start(INVENTORY, f"scan_root={create_tree(root / 'tree').as_posix()}")
    assert code == 0
    written["completed"] = space.report(session_id)

    (root / "empty").mkdir()
    code, session_id = space.start(INVENTORY, f"scan_root={(root / 'empty').as_posix()}")
    assert code == 3
    written["failed"] = space.report(session_id)

    _, init = space.run(
        ["init-new-session", "--workflow-file", INVENTORY.as_posix(), "--max-nodes-visited", str(BUDGET)]
    )
    session_id = cast(str, init["session_id"])
    space.run(["set-input", "--session-id", session_id, "--input", f"scan_root={(root / 'tree').as_posix()}"])
    code, _ = space.run(["resume", "--session-id", session_id])
    assert code == 2
    written["budget"] = space.report(session_id)

    source = root / "contract.txt"
    source.write_text("terms")
    (root / "target").mkdir()
    code, session_id = space.start(
        APPROVE_AND_COPY, f"source_file={source.as_posix()}", f"target_dir={(root / 'target').as_posix()}"
    )
    assert code == 2
    written["question"] = space.report(session_id)

    yield written
