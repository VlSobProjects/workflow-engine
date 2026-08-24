"""ADR 012 end-to-end: the shipped folder-inventory template, parameterized and exported in one run."""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.cli.main import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "folder-inventory-to-csv.json"


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "workflow_engine_config.json"
    config_path.write_text(
        json.dumps({"work_dir": (tmp_path / "engine").as_posix(), "external_modules": [], "storage": {}})
    )
    return config_path.absolute()


def test_folder_inventory_parameterized_run_exports_csv(tmp_path, capsys):
    scan = tmp_path / "scan"
    (scan / "sub").mkdir(parents=True)
    (scan / "a.txt").write_text("alpha")
    (scan / "sub" / "b.txt").write_text("beta")
    out = tmp_path / "out"
    config = _write_config(tmp_path)

    code, response = run_json_cli(
        [
            "run",
            "--workflow-file",
            EXAMPLE.as_posix(),
            "--input",
            f"scan_root:Path={scan.as_posix()}",
            "--export-dir",
            out.as_posix(),
            "--config",
            config.as_posix(),
        ],
        capsys,
    )

    assert code == 0
    assert response["workflow_status"] == "completed"
    assert cast(dict, response["data"])["deliverables"] == ["file_scan_table", "file_scan_report"]

    exported = out / "reports" / "file_scan_table.csv"
    assert exported.is_file()
    content = exported.read_text()
    assert f"{scan.resolve().as_posix()},a.txt" in content
    assert f"{(scan / 'sub').resolve().as_posix()},b.txt" in content

    document = out / "reports" / "file_scan_report.txt"
    assert document.is_file()
    assert document.read_text(encoding="utf-8").splitlines()[0] == scan.resolve().as_posix()
