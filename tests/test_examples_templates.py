"""End-to-end coverage of the two templates shipped in `examples/`.

Each template is run through the installed CLI entry point on a temporary tree: once on its success
path, and once on the failure the README warns about. The failure paths exist because both templates
declare a deliverable, so a run that produces no artifact must fail instead of reporting success.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
INVENTORY_TEMPLATE = EXAMPLES_DIR / "folder-inventory-to-csv.json"
FLATTEN_TEMPLATE = EXAMPLES_DIR / "flatten-copy-tree.json"


@pytest.fixture
def create_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "workflow_engine_config.json"
    config_path.write_text(
        json.dumps({"work_dir": (tmp_path / "runtime").as_posix(), "external_modules": [], "storage": {}})
    )
    return config_path


def create_tree(root: Path) -> None:
    """Two files in the root and one in a nested folder, so the walk has to recurse."""
    (root / "nested").mkdir(parents=True)
    (root / "first.txt").write_text("first")
    (root / "second.txt").write_text("second")
    (root / "nested" / "third.txt").write_text("third")


def run_template(template: Path, inputs: list[str], config_path: Path, capsys) -> tuple[int, dict[str, object]]:
    argv = ["run", "--workflow-file", template.as_posix(), "--config", config_path.as_posix(), "--json"]
    for assignment in inputs:
        argv += ["--input", assignment]
    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def artifact_path(response: dict[str, object], name: str) -> Path:
    artifacts = cast(dict[str, dict[str, str]], cast(dict[str, object], response["data"])["artifacts"])
    return Path(artifacts[name]["path"])


class TestFolderInventoryToCsv:
    def test_the_scan_writes_its_csv_deliverable(self, tmp_path: Path, create_config, capsys):
        scan_root = tmp_path / "scan-root"
        create_tree(scan_root)

        code, response = run_template(
            INVENTORY_TEMPLATE, [f"scan_root:Path={scan_root.as_posix()}"], create_config, capsys
        )

        assert code == 0
        assert response["workflow_status"] == "completed"
        report = artifact_path(response, "file_scan_table")
        assert report.is_file()
        lines = report.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "Folder,Name,Size,MIME,Modified,MD5"
        assert len(lines) == 4

    def test_the_scan_writes_a_table_per_folder_as_its_second_deliverable(self, tmp_path: Path, create_config, capsys):
        """The operator's report: one flat table over the whole tree cannot be read (ADR 020)."""

        scan_root = tmp_path / "scan-root"
        create_tree(scan_root)

        code, response = run_template(
            INVENTORY_TEMPLATE, [f"scan_root:Path={scan_root.as_posix()}"], create_config, capsys
        )

        assert code == 0
        document = artifact_path(response, "file_scan_report").read_text(encoding="utf-8")
        assert document.splitlines()[0] == scan_root.as_posix()
        assert (scan_root / "nested").as_posix() in document
        assert "Folder" not in document
        assert "third.txt" in document

    def test_a_scan_without_files_fails_instead_of_reporting_success(self, tmp_path: Path, create_config, capsys):
        scan_root = tmp_path / "empty-root"
        scan_root.mkdir()

        code, response = run_template(
            INVENTORY_TEMPLATE, [f"scan_root:Path={scan_root.as_posix()}"], create_config, capsys
        )

        assert code == 3
        assert response["workflow_status"] == "failed"
        data = cast(dict[str, object], response["data"])
        assert data["current_node"] == "WRITE_TABLE"
        assert data["artifacts"] == {}
        assert "pretty_table_no_data" in cast(dict[str, str], response["errors"])["WRITE_TABLE"]


class TestFlattenCopyTree:
    def test_every_file_is_copied_and_reported(self, tmp_path: Path, create_config, capsys):
        source_root = tmp_path / "source-root"
        create_tree(source_root)
        target_dir = tmp_path / "flat"
        target_dir.mkdir()

        code, response = run_template(
            FLATTEN_TEMPLATE,
            [f"source_root:Path={source_root.as_posix()}", f"target_dir:Path={target_dir.as_posix()}"],
            create_config,
            capsys,
        )

        assert code == 0
        assert response["workflow_status"] == "completed"
        assert sorted(path.name for path in target_dir.iterdir()) == ["first.txt", "second.txt", "third.txt"]
        report = artifact_path(response, "copy_report")
        assert report.is_file()
        assert report.read_text(encoding="utf-8").splitlines()[0] == "Source,Copied,MD5"

    def test_a_missing_target_directory_fails_the_copy_node(self, tmp_path: Path, create_config, capsys):
        source_root = tmp_path / "source-root"
        create_tree(source_root)
        target_dir = tmp_path / "does-not-exist"

        code, response = run_template(
            FLATTEN_TEMPLATE,
            [f"source_root:Path={source_root.as_posix()}", f"target_dir:Path={target_dir.as_posix()}"],
            create_config,
            capsys,
        )

        assert code == 3
        assert response["workflow_status"] == "failed"
        # The run must stop at the copy node: without its failure transition it walks on to
        # COLLECT_ROW and dies there on the parameter the failed copy never wrote.
        assert cast(dict[str, object], response["data"])["current_node"] == "COPY_FILE"
        errors = cast(dict[str, str], response["errors"])
        assert list(errors) == ["COPY_FILE"]
        assert "target_folder_not_found" in errors["COPY_FILE"]
