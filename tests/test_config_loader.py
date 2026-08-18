import json
from pathlib import Path

import pytest

from workflow_engine.bootstrap.config_loader import (
    DEFAULT_HARD_MAX_NODES_VISITED,
    WorkflowEngineConfiguration,
    load_config_file,
)
from workflow_engine.exceptions import WorkflowConfigurationError


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


def test_default_hard_cap_is_applied_and_written_to_the_default_config(tmp_path: Path):
    config = load_config_file(cwd=tmp_path)

    assert config.hard_max_nodes_visited == DEFAULT_HARD_MAX_NODES_VISITED
    written = json.loads((tmp_path / ".workflow-engine" / "workflow_engine_config.json").read_text())
    assert written["hard_max_nodes_visited"] == DEFAULT_HARD_MAX_NODES_VISITED


def test_hard_cap_override_is_read_from_the_config_file(tmp_path: Path):
    config_path = tmp_path / ".workflow-engine" / "workflow_engine_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"hard_max_nodes_visited": 5000}')

    config = load_config_file(cwd=tmp_path)

    assert config.hard_max_nodes_visited == 5000


def test_a_non_positive_hard_cap_in_the_config_file_is_rejected(tmp_path: Path):
    config_path = tmp_path / ".workflow-engine" / "workflow_engine_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"hard_max_nodes_visited": 0}')

    with pytest.raises(WorkflowConfigurationError):
        load_config_file(cwd=tmp_path)


def test_the_configuration_rejects_a_non_positive_hard_cap():
    with pytest.raises(WorkflowConfigurationError):
        WorkflowEngineConfiguration(hard_max_nodes_visited=-1)


def test_environment_storage_dir_override_has_priority_over_work_dir_env(tmp_path: Path, monkeypatch):
    custom_work_dir = tmp_path / "env-work"
    custom_storage_dir = tmp_path / "env-storage"
    monkeypatch.setenv("WE_WORK_DIR", custom_work_dir.as_posix())
    monkeypatch.setenv("WE_STORAGE_DIR", custom_storage_dir.as_posix())

    config = load_config_file(cwd=tmp_path)

    assert config.work_dir == custom_work_dir.resolve().as_posix()
    assert config.storage["storage_dir"] == custom_storage_dir.resolve().as_posix()
