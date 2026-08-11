from pathlib import Path

from workflow_engine.bootstrap.config_loader import load_config_file


def test_default_config_uses_runtime_root_and_creates_default_config(tmp_path: Path):
    config = load_config_file(cwd=tmp_path)

    runtime_root = (tmp_path / ".workflow-engine").resolve()
    assert config.work_dir == runtime_root.as_posix()
    assert config.storage["storage_dir"] == (runtime_root / "json-storage").as_posix()
    assert (runtime_root / "workflow_engine_config.json").exists()


def test_work_dir_override_sets_runtime_root_and_default_storage(tmp_path: Path):
    custom_work_dir = tmp_path / "custom-work"
    config = load_config_file(cwd=tmp_path, work_dir_override=custom_work_dir.as_posix())

    assert config.work_dir == custom_work_dir.resolve().as_posix()
    assert config.storage["storage_dir"] == (custom_work_dir / "json-storage").resolve().as_posix()


def test_storage_dir_override_is_used_directly(tmp_path: Path):
    custom_storage_dir = tmp_path / "custom-storage"
    config = load_config_file(cwd=tmp_path, storage_dir_override=custom_storage_dir.as_posix())

    assert config.work_dir == (tmp_path / ".workflow-engine").resolve().as_posix()
    assert config.storage["storage_dir"] == custom_storage_dir.resolve().as_posix()


def test_environment_work_dir_override_has_priority_over_config_defaults(tmp_path: Path, monkeypatch):
    config_path = tmp_path / ".workflow-engine" / "workflow_engine_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"work_dir": "from-config", "storage": {"storage_dir": "from-config-storage"}}')

    custom_work_dir = tmp_path / "env-work"
    monkeypatch.setenv("WE_WORK_DIR", custom_work_dir.as_posix())

    config = load_config_file(cwd=tmp_path)

    assert config.work_dir == custom_work_dir.resolve().as_posix()
    assert config.storage["storage_dir"] == (custom_work_dir / "json-storage").resolve().as_posix()
