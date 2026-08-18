"""ADR 011 increment 3: the export-artifact command, --export-dir and additive result keys."""

import json
from pathlib import Path
from typing import cast

import pytest

from tests.test_adr009_e2e_copy_tree import build_workflow, create_source_tree
from workflow_engine.cli.main import main


def run_json_cli(argv: list[str], capsys) -> tuple[int, dict[str, object]]:
    with pytest.raises(SystemExit) as exc_info:
        main([*argv, "--json"])
    return cast(int, exc_info.value.code), cast(dict[str, object], json.loads(capsys.readouterr().out))


def _write_config(tmp_path: Path, extra: dict[str, object] | None = None) -> Path:
    config_path = tmp_path / "workflow_engine_config.json"
    config_data: dict[str, object] = {"work_dir": tmp_path.as_posix(), "external_modules": [], "storage": {}}
    config_data.update(extra or {})
    config_path.write_text(json.dumps(config_data))
    return config_path.absolute()


def _artifact_workflow(tmp_path: Path, with_deliverables: bool) -> Path:
    source_root = tmp_path / "source-root"
    create_source_tree(source_root)
    target_dir = tmp_path / "copy-target"
    target_dir.mkdir()
    workflow = build_workflow(source_root, target_dir)
    if with_deliverables:
        workflow["deliverables"] = ["copy_report"]
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow, indent=2))
    return workflow_path


def _run(tmp_path: Path, config: Path, capsys, extra_argv: list[str] | None = None) -> tuple[int, dict[str, object]]:
    workflow_path = _artifact_workflow(tmp_path, with_deliverables=True)
    return run_json_cli(
        ["run", "--workflow-file", workflow_path.as_posix(), "--config", config.as_posix(), *(extra_argv or [])],
        capsys,
    )


def test_export_artifact_requires_name_or_all(tmp_path, capsys):
    config = _write_config(tmp_path)
    _, run_response = _run(tmp_path, config, capsys)
    session_id = cast(str, run_response["session_id"])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "export-artifact",
                "--session-id",
                session_id,
                "--target-dir",
                (tmp_path / "out").as_posix(),
                "--config",
                config.as_posix(),
                "--json",
            ]
        )
    assert exc_info.value.code == 4


def test_export_artifact_name_and_all_are_mutually_exclusive(tmp_path, capsys):
    config = _write_config(tmp_path)
    _, run_response = _run(tmp_path, config, capsys)
    session_id = cast(str, run_response["session_id"])

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "export-artifact",
                "--session-id",
                session_id,
                "--target-dir",
                (tmp_path / "out").as_posix(),
                "--artifact-name",
                "copy_report",
                "--all",
                "--config",
                config.as_posix(),
                "--json",
            ]
        )
    assert exc_info.value.code == 4


def test_export_artifact_by_name_copies_file(tmp_path, capsys):
    config = _write_config(tmp_path)
    _, run_response = _run(tmp_path, config, capsys)
    session_id = cast(str, run_response["session_id"])
    out_dir = tmp_path / "out-by-name"

    code, response = run_json_cli(
        [
            "export-artifact",
            "--session-id",
            session_id,
            "--target-dir",
            out_dir.as_posix(),
            "--artifact-name",
            "copy_report",
            "--config",
            config.as_posix(),
        ],
        capsys,
    )

    assert code == 0
    assert (out_dir / "reports" / "copy_report.csv").is_file()
    exported = cast(dict[str, object], cast(dict[str, object], response["data"])["exported"])
    assert "copy_report" in exported


def test_export_artifact_all_exports_declared_deliverables(tmp_path, capsys):
    config = _write_config(tmp_path)
    _, run_response = _run(tmp_path, config, capsys)
    session_id = cast(str, run_response["session_id"])
    out_dir = tmp_path / "out-all"

    code, _ = run_json_cli(
        [
            "export-artifact",
            "--session-id",
            session_id,
            "--target-dir",
            out_dir.as_posix(),
            "--all",
            "--config",
            config.as_posix(),
        ],
        capsys,
    )

    assert code == 0
    assert (out_dir / "reports" / "copy_report.csv").is_file()


def test_export_artifact_all_without_deliverables_is_error(tmp_path, capsys):
    config = _write_config(tmp_path)
    workflow_path = _artifact_workflow(tmp_path, with_deliverables=False)
    _, run_response = run_json_cli(
        ["run", "--workflow-file", workflow_path.as_posix(), "--config", config.as_posix()], capsys
    )
    session_id = cast(str, run_response["session_id"])

    code, response = run_json_cli(
        [
            "export-artifact",
            "--session-id",
            session_id,
            "--target-dir",
            (tmp_path / "out").as_posix(),
            "--all",
            "--config",
            config.as_posix(),
        ],
        capsys,
    )

    assert code == 4
    assert response["command_status"] == "error"


def test_export_artifact_unknown_name_is_error(tmp_path, capsys):
    config = _write_config(tmp_path)
    _, run_response = _run(tmp_path, config, capsys)
    session_id = cast(str, run_response["session_id"])

    code, response = run_json_cli(
        [
            "export-artifact",
            "--session-id",
            session_id,
            "--target-dir",
            (tmp_path / "out").as_posix(),
            "--artifact-name",
            "no_such_artifact",
            "--config",
            config.as_posix(),
        ],
        capsys,
    )

    assert code == 4
    assert response["command_status"] == "error"


def test_export_dir_cli_option_overrides_config(tmp_path, capsys):
    config_dir = tmp_path / "config-export"
    cli_dir = tmp_path / "cli-export"
    config = _write_config(tmp_path, {"export_dir": config_dir.as_posix()})

    _run(tmp_path, config, capsys, extra_argv=["--export-dir", cli_dir.as_posix()])

    assert (cli_dir / "reports" / "copy_report.csv").is_file()
    assert not config_dir.exists()


def test_export_dir_falls_back_to_config(tmp_path, capsys):
    config_dir = tmp_path / "config-export"
    config = _write_config(tmp_path, {"export_dir": config_dir.as_posix()})

    _run(tmp_path, config, capsys)

    assert (config_dir / "reports" / "copy_report.csv").is_file()


def test_run_result_surfaces_artifacts_and_deliverables(tmp_path, capsys):
    config = _write_config(tmp_path)
    _, response = _run(tmp_path, config, capsys)

    data = cast(dict[str, object], response["data"])
    assert data["deliverables"] == ["copy_report"]
    artifacts = cast(dict[str, dict[str, str]], data["artifacts"])
    assert "copy_report" in artifacts
    assert artifacts["copy_report"]["path"].endswith("artifacts/reports/copy_report.csv")


def test_show_state_surfaces_absolute_artifacts_and_deliverables(tmp_path, capsys):
    config = _write_config(tmp_path)
    _, run_response = _run(tmp_path, config, capsys)
    session_id = cast(str, run_response["session_id"])

    code, response = run_json_cli(["show-state", "--session-id", session_id, "--config", config.as_posix()], capsys)

    assert code == 0
    data = cast(dict[str, object], response["data"])
    assert data["deliverables"] == ["copy_report"]
    assert "copy_report" in cast(dict[str, str], data["artifacts"])
    assert "copy_report" in cast(dict[str, dict[str, str]], data["artifacts_absolute"])
