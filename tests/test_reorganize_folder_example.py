"""The `reorganize-folder` example: the class 4 measurement build of roadmap step 10.

The shipped definition is run end to end through the CLI with the `fake` adapter scripted in the
`providers` section, so the model steps run without a network. What each run measures is what the
example exists to show: files hashed and grouped by content in code before any model reads them
(the dictionary family of ADR 006), a dictionary answer whose keys are checked by the
`is_answer_keys_valid` guard before the value lands (gap G4), the re-ask of a decision whose keys
do not fit, bounded by `max_attempts`, and the deterministic refusal of an empty tree before a
single model call.
"""

import csv
import json
from pathlib import Path
from typing import cast

import pytest

import workflow_engine.providers.fake_provider  # noqa: F401 - registers the `fake` adapter before any test runs
from workflow_engine.cli.main import main

TEMPLATE = Path(__file__).resolve().parents[1] / "examples" / "reorganize-folder.json"

CATEGORIES = 'categories:list=["documents", "images", "other"]'

ALPHA_TEXT = "the alpha content\n"


def classify(category: str) -> str:
    return json.dumps({"file_category": category, "category_reason": f"Looks like {category}."})


def plan_reply(root: Path, counts: dict[str, int]) -> str:
    keep = (root / "a.txt").as_posix()
    doomed = (root / "docs" / "copy-of-a.txt").as_posix()
    return json.dumps(
        {
            "plan_text": f"Move every text file into documents and the image into images. Keep {keep} "
            f"and delete {doomed}, its identical copy.",
            "moves": {
                keep: "documents",
                (root / "docs" / "b.txt").as_posix(): "documents",
                (root / "img.png").as_posix(): "images",
            },
            "counts_by_category": counts,
        }
    )


def build_workspace(tmp_path: Path, replies: list[object]) -> dict[str, str]:
    config = tmp_path / "workflow_engine_config.json"
    config.write_text(
        json.dumps(
            {
                "work_dir": (tmp_path / "runtime").as_posix(),
                "external_modules": [],
                "storage": {},
                "providers": {"local": {"adapter": "fake", "model": "small-1", "options": {"replies": replies}}},
            }
        ),
        encoding="utf-8",
    )
    return {"config": config.as_posix(), "runtime": (tmp_path / "runtime").as_posix()}


def run_example(workspace: dict[str, str], scan_root: Path, capsys) -> tuple[int, dict[str, object]]:
    argv = [
        "run",
        "--workflow-file",
        TEMPLATE.as_posix(),
        "--config",
        workspace["config"],
        "--json",
        "--input",
        f"scan_root:Path={scan_root.as_posix()}",
        "--input",
        CATEGORIES,
    ]
    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def artifacts_of(response: dict[str, object]) -> dict[str, dict[str, str]]:
    return cast(dict[str, dict[str, str]], cast(dict[str, object], response["data"])["artifacts"])


def calls_of(workspace: dict[str, str], response: dict[str, object]) -> list[dict[str, object]]:
    session_id = cast(str, response["session_id"])
    path = Path(workspace["runtime"]) / "json-storage" / session_id / "records.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [
        record
        for record in records
        if isinstance(record.get("details"), dict) and "provider" in cast(dict[str, object], record["details"])
    ]


def duplicated_tree(root: Path) -> Path:
    """Four files, two of them identical by content under different names in different folders."""
    (root / "docs").mkdir(parents=True)
    (root / "a.txt").write_text(ALPHA_TEXT, encoding="utf-8")
    (root / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (root / "docs" / "b.txt").write_text("the beta content\n", encoding="utf-8")
    (root / "docs" / "copy-of-a.txt").write_text(ALPHA_TEXT, encoding="utf-8")
    return root


# The walk pops the sorted root entries first, then what ENQUEUE appended: a.txt, img.png,
# then docs/b.txt, docs/copy-of-a.txt. One classification per file, in that order.
CLASSIFY_REPLIES = [classify("documents"), classify("images"), classify("documents"), classify("documents")]


class TestPlanPath:
    def test_the_run_plans_the_tree_and_exports_both_deliverables(self, tmp_path, capsys):
        root = duplicated_tree(tmp_path / "tree")
        replies: list[object] = [*CLASSIFY_REPLIES, plan_reply(root, {"documents": 3, "images": 1})]
        workspace = build_workspace(tmp_path, replies)

        code, response = run_example(workspace, root, capsys)

        assert code == 0
        artifacts = artifacts_of(response)
        assert set(artifacts) >= {"reorg_plan", "inventory_table"}

        plan = Path(artifacts["reorg_plan"]["path"]).read_text(encoding="utf-8")
        assert "Move every text file into documents" in plan
        assert '"documents":3' in plan
        # The duplicate group was found by the hash grouping in code and rendered from its parameter.
        assert (root / "a.txt").as_posix() in plan
        assert (root / "docs" / "copy-of-a.txt").as_posix() in plan

    def test_identical_files_share_their_hash_in_the_table(self, tmp_path, capsys):
        root = duplicated_tree(tmp_path / "tree")
        replies: list[object] = [*CLASSIFY_REPLIES, plan_reply(root, {"documents": 3, "images": 1})]
        workspace = build_workspace(tmp_path, replies)

        code, response = run_example(workspace, root, capsys)

        assert code == 0
        table = Path(artifacts_of(response)["inventory_table"]["path"])
        rows = {row["Name"]: row for row in csv.DictReader(table.read_text(encoding="utf-8").splitlines())}
        assert len(rows) == 4
        assert rows["a.txt"]["MD5"] == rows["copy-of-a.txt"]["MD5"]
        assert rows["a.txt"]["MD5"] != rows["b.txt"]["MD5"]

    def test_one_call_per_file_and_one_decision(self, tmp_path, capsys):
        root = duplicated_tree(tmp_path / "tree")
        replies: list[object] = [*CLASSIFY_REPLIES, plan_reply(root, {"documents": 3, "images": 1})]
        workspace = build_workspace(tmp_path, replies)

        code, response = run_example(workspace, root, capsys)

        assert code == 0
        assert len(calls_of(workspace, response)) == 5


class TestAnswerKeysGuard:
    def test_a_decision_with_invented_keys_is_asked_again(self, tmp_path, capsys):
        root = duplicated_tree(tmp_path / "tree")
        replies: list[object] = [
            *CLASSIFY_REPLIES,
            plan_reply(root, {"invented": 4}),
            plan_reply(root, {"documents": 3, "images": 1}),
        ]
        workspace = build_workspace(tmp_path, replies)

        code, response = run_example(workspace, root, capsys)

        assert code == 0
        # Four classifications and two decisions: the first decision bound cleanly but its
        # `counts_by_category` keys were not in the configured list, so the guard sent it back.
        assert len(calls_of(workspace, response)) == 6

    def test_a_decision_that_never_fits_exhausts_its_attempts(self, tmp_path, capsys):
        root = duplicated_tree(tmp_path / "tree")
        replies: list[object] = [
            *CLASSIFY_REPLIES,
            plan_reply(root, {"invented": 4}),
            plan_reply(root, {"invented": 4}),
            plan_reply(root, {"invented": 4}),
        ]
        workspace = build_workspace(tmp_path, replies)

        code, response = run_example(workspace, root, capsys)

        assert code == 3
        assert "max_attempts_exceeded" in json.dumps(response)


class TestEmptyTree:
    def test_an_empty_tree_is_refused_before_any_model_call(self, tmp_path, capsys):
        root = tmp_path / "tree"
        (root / "only-folders" / "nested").mkdir(parents=True)
        workspace = build_workspace(tmp_path, [])

        code, response = run_example(workspace, root, capsys)

        assert code == 3
        assert "nothing_to_plan" in json.dumps(response)
        assert calls_of(workspace, response) == []
