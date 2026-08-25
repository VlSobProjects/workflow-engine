"""The three named variants of the inventory example: the class 4 evidence of ADR 014.

Each variant is a shipped definition run end to end through the installed CLI, with the `fake`
adapter scripted in the `providers` section of the engine configuration, so the model steps of a
real workflow are exercised without a network. What each run measures is the thing its variant
exists to show: a guard that sends only the listed formats to a model (`described`), a second step
that chooses its own model over what the first one accumulated (`tiered`), and a refusal on
`context_overflow` answered by splitting the file and calling the model per part (`chunked`). Every
variant is run once on its success path and once on the failure it adds.
"""

import csv
import json
from pathlib import Path
from typing import cast

import pytest

import workflow_engine.providers.fake_provider  # noqa: F401 - registers the `fake` adapter before any test runs
from workflow_engine.cli.main import main

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
DESCRIBED = EXAMPLES_DIR / "folder-inventory-to-csv-described.json"
TIERED = EXAMPLES_DIR / "folder-inventory-to-csv-tiered.json"
CHUNKED = EXAMPLES_DIR / "folder-inventory-to-csv-chunked.json"

TEXT_FORMATS = 'described_formats:list=["text/plain"]'

# Two chunks of the 2000 character budget the shipped definition declares, cut on the newline between them.
BIG_FILE_TEXT = "A" * 1900 + "\n" + "B" * 1900 + "\n"

OVERFLOW = {"error": "context_overflow", "message": "exceeds the available context size"}
NO_SUCH_MODEL = {"error": "permanent", "message": "no such model"}

TIERED_REPLIES: list[object] = ["Holds the alpha text.", "Holds the gamma text.", "1. Archive the png."]
CHUNKED_REPLIES: list[object] = [
    OVERFLOW,
    "The first part is all A.",
    "The second part is all B.",
    "A file of A followed by B.",
    "The small file.",
]


def build_workspace(tmp_path: Path, replies: list[object]) -> dict[str, str]:
    """A workspace whose configuration scripts the `fake` adapter under the provider name the examples use."""
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


def run_variant(template: Path, workspace: dict[str, str], scan_root: Path, capsys) -> tuple[int, dict[str, object]]:
    argv = [
        "run",
        "--workflow-file",
        template.as_posix(),
        "--config",
        workspace["config"],
        "--json",
        "--input",
        f"scan_root:Path={scan_root.as_posix()}",
        "--input",
        TEXT_FORMATS,
    ]
    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def artifacts_of(response: dict[str, object]) -> dict[str, dict[str, str]]:
    return cast(dict[str, dict[str, str]], cast(dict[str, object], response["data"])["artifacts"])


def rows_of(response: dict[str, object], name: str = "file_scan_table") -> dict[str, dict[str, str]]:
    path = Path(artifacts_of(response)[name]["path"])
    return {row["Name"]: row for row in csv.DictReader(path.read_text(encoding="utf-8").splitlines())}


def records_of(workspace: dict[str, str], response: dict[str, object]) -> list[dict[str, object]]:
    session_id = cast(str, response["session_id"])
    path = Path(workspace["runtime"]) / "json-storage" / session_id / "records.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def calls_of(workspace: dict[str, str], response: dict[str, object]) -> list[dict[str, object]]:
    """The record of every visit that made a model call, in the order the calls were made."""
    return [
        record
        for record in records_of(workspace, response)
        if isinstance(record.get("details"), dict) and "provider" in cast(dict[str, object], record["details"])
    ]


def details_of(call: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], call["details"])


def mixed_tree(root: Path) -> Path:
    """One described file, one file of a format the parameter does not list, one described file below."""
    (root / "nested").mkdir(parents=True)
    (root / "alpha.txt").write_text("the alpha file", encoding="utf-8")
    (root / "beta.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (root / "nested" / "gamma.txt").write_text("the gamma file", encoding="utf-8")
    return root


def big_and_small_tree(root: Path) -> Path:
    """One file the model refuses as too large, and one it answers as it stands."""
    root.mkdir()
    (root / "big.txt").write_text(BIG_FILE_TEXT, encoding="utf-8")
    (root / "small.txt").write_text("the small file", encoding="utf-8")
    return root


class TestDescribed:
    def test_only_the_listed_formats_reach_the_model_and_the_row_carries_what_it_said(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, ["Holds the alpha text.", "Holds the gamma text."])

        code, response = run_variant(DESCRIBED, workspace, mixed_tree(tmp_path / "scan-root"), capsys)

        assert code == 0, response
        assert response["workflow_status"] == "completed"
        rows = rows_of(response)
        assert sorted(rows) == ["alpha.txt", "beta.png", "gamma.txt"]
        assert rows["alpha.txt"]["Description"] == "Holds the alpha text."
        assert rows["gamma.txt"]["Description"] == "Holds the gamma text."
        assert rows["beta.png"]["Description"] == "not described"

    def test_the_model_is_called_once_per_listed_file_and_every_call_is_accounted_for(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, ["Holds the alpha text.", "Holds the gamma text."])

        _, response = run_variant(DESCRIBED, workspace, mixed_tree(tmp_path / "scan-root"), capsys)

        calls = calls_of(workspace, response)
        assert [call["node_id"] for call in calls] == ["DESCRIBE", "DESCRIBE"]
        for call in calls:
            details = details_of(call)
            assert (details["provider"], details["model"], details["status"]) == ("local", "small-1", "answered")

    def test_every_call_leaves_its_prompt_and_its_reply_as_artifacts(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, ["Holds the alpha text.", "Holds the gamma text."])

        _, response = run_variant(DESCRIBED, workspace, mixed_tree(tmp_path / "scan-root"), capsys)

        artifacts = artifacts_of(response)
        assert "DESCRIBE.prompt.1.1" in artifacts
        assert "DESCRIBE.reply.2.1" in artifacts
        assert "the alpha file" in Path(artifacts["DESCRIBE.prompt.1.1"]["path"]).read_text(encoding="utf-8")
        assert Path(artifacts["DESCRIBE.reply.2.1"]["path"]).read_text(encoding="utf-8") == "Holds the gamma text."

    def test_a_file_that_does_not_read_as_text_keeps_its_row(self, tmp_path, capsys):
        """The listed format is a guess from the name; the bytes decide, and a run must not die of it."""

        workspace = build_workspace(tmp_path, ["Holds the alpha text."])
        scan_root = tmp_path / "scan-root"
        scan_root.mkdir()
        (scan_root / "alpha.txt").write_text("the alpha file", encoding="utf-8")
        (scan_root / "broken.txt").write_bytes(b"\xff\xfe\x00binary\x00")

        code, response = run_variant(DESCRIBED, workspace, scan_root, capsys)

        assert code == 0, response
        assert rows_of(response)["broken.txt"]["Description"] == "not described"

    def test_a_model_that_fails_permanently_fails_the_run_instead_of_filling_the_table_with_excuses(
        self, tmp_path, capsys
    ):
        workspace = build_workspace(tmp_path, [NO_SUCH_MODEL])

        code, response = run_variant(DESCRIBED, workspace, mixed_tree(tmp_path / "scan-root"), capsys)

        assert code == 3
        assert response["workflow_status"] == "failed"
        assert cast(dict[str, object], response["data"])["current_node"] == "DESCRIBE"
        assert "description_unavailable" in cast(dict[str, str], response["errors"])["DESCRIBE"]

    def test_a_transient_failure_is_retried_and_both_calls_are_recorded(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, [{"error": "transient", "message": "busy"}, "Holds the alpha text."])
        scan_root = tmp_path / "scan-root"
        scan_root.mkdir()
        (scan_root / "alpha.txt").write_text("the alpha file", encoding="utf-8")

        code, response = run_variant(DESCRIBED, workspace, scan_root, capsys)

        assert code == 0, response
        assert [details_of(call)["status"] for call in calls_of(workspace, response)] == ["failed", "answered"]
        assert rows_of(response)["alpha.txt"]["Description"] == "Holds the alpha text."


class TestTiered:
    def test_the_second_step_reads_the_table_and_writes_the_proposal_as_the_second_deliverable(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, list(TIERED_REPLIES))

        code, response = run_variant(TIERED, workspace, mixed_tree(tmp_path / "scan-root"), capsys)

        assert code == 0, response
        assert response["workflow_status"] == "completed"
        artifacts = artifacts_of(response)
        assert sorted(name for name in artifacts if "." not in name) == ["file_scan_table", "optimization_proposal"]
        assert Path(artifacts["optimization_proposal"]["path"]).read_text(encoding="utf-8") == "1. Archive the png."
        proposal_prompt = Path(artifacts["PROPOSE.prompt.1.1"]["path"]).read_text(encoding="utf-8")
        assert "Holds the alpha text." in proposal_prompt
        assert "not described" in proposal_prompt

    def test_the_describing_step_takes_the_model_of_the_provider_and_the_proposal_names_its_own(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, list(TIERED_REPLIES))

        _, response = run_variant(TIERED, workspace, mixed_tree(tmp_path / "scan-root"), capsys)

        models = {cast(str, call["node_id"]): details_of(call)["model"] for call in calls_of(workspace, response)}
        assert models == {"DESCRIBE": "small-1", "PROPOSE": "a-publisher/a-larger-model"}

    def test_a_proposal_the_model_cannot_produce_fails_the_run_that_declared_it(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, [*TIERED_REPLIES[:2], NO_SUCH_MODEL])

        code, response = run_variant(TIERED, workspace, mixed_tree(tmp_path / "scan-root"), capsys)

        assert code == 3
        assert cast(dict[str, object], response["data"])["current_node"] == "PROPOSE"
        assert "proposal_unavailable" in cast(dict[str, str], response["errors"])["PROPOSE"]
        assert "optimization_proposal" not in artifacts_of(response)


class TestChunked:
    def test_a_file_the_model_refuses_is_described_part_by_part_into_the_same_column(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, list(CHUNKED_REPLIES))

        code, response = run_variant(CHUNKED, workspace, big_and_small_tree(tmp_path / "scan-root"), capsys)

        assert code == 0, response
        rows = rows_of(response)
        assert rows["big.txt"]["Description"] == "A file of A followed by B."
        assert rows["small.txt"]["Description"] == "The small file."

    def test_the_refusal_and_every_call_of_the_loop_are_in_the_record_stream(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, list(CHUNKED_REPLIES))

        _, response = run_variant(CHUNKED, workspace, big_and_small_tree(tmp_path / "scan-root"), capsys)

        calls = calls_of(workspace, response)
        assert [call["node_id"] for call in calls] == [
            "DESCRIBE",
            "DESCRIBE_CHUNK",
            "DESCRIBE_CHUNK",
            "SUMMARIZE_PARTS",
            "DESCRIBE",
        ]
        refusal = details_of(calls[0])
        assert (refusal["status"], refusal["error_class"]) == ("failed", "context_overflow")
        # One record per call rather than one slot overwritten: the two parts of one file are told
        # apart only here, and their artifacts carry the same two ordinals. See ADR 014 §4.
        assert "DESCRIBE_CHUNK.reply.2.1" in artifacts_of(response)

    def test_a_part_the_model_still_refuses_fails_the_run_rather_than_splitting_again(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, [OVERFLOW, OVERFLOW])

        code, response = run_variant(CHUNKED, workspace, big_and_small_tree(tmp_path / "scan-root"), capsys)

        assert code == 3
        assert cast(dict[str, object], response["data"])["current_node"] == "DESCRIBE_CHUNK"
        assert "chunk_too_large" in cast(dict[str, str], response["errors"])["DESCRIBE_CHUNK"]
