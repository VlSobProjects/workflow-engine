import hashlib
import json
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.engine import WorkflowEngine
from workflow_engine.output import ActionNodeOutput, ParamWrite, WriteParamMode
from workflow_engine.registry.function_registry import register_function


def create_engine(tmp_path: Path) -> WorkflowEngine:
    bootstrap = Bootstrap(WorkflowEngineConfiguration(work_dir=tmp_path.as_posix()))
    return bootstrap.build_engine()


@register_function
def adr006_seed_scan_queue(root_path: str, queue_param_name: str, rows_param_name: str) -> ActionNodeOutput:
    root = Path(root_path).resolve()
    return ActionNodeOutput(
        output_text=root.as_posix(),
        param_writes={
            queue_param_name: ParamWrite(mode=WriteParamMode.SET, value=deque([root.as_posix()])),
            rows_param_name: ParamWrite(mode=WriteParamMode.SET, value=[]),
        },
    )


@register_function
def adr006_enqueue_folder_entries(folder_path: str, queue_param_name: str) -> ActionNodeOutput:
    folder = Path(folder_path)
    if not folder.is_dir():
        return ActionNodeOutput(
            output_text="",
            error_code="folder_not_found",
            error_msg=f"Folder '{folder_path}' does not exist",
        )

    entries = sorted(item.resolve().as_posix() for item in folder.iterdir() if item.is_dir() or item.is_file())
    if len(entries) > 0:
        return ActionNodeOutput(
            output_text=folder.resolve().as_posix(),
            param_writes={queue_param_name: ParamWrite(mode=WriteParamMode.EXTEND, value=entries)},
        )
    return ActionNodeOutput(output_text=folder.resolve().as_posix())


@register_function
def adr006_pass_path(file_path: str) -> ActionNodeOutput:
    return ActionNodeOutput(output_text=file_path)


@register_function
def adr006_emit_param(param_name: str, state) -> ActionNodeOutput:
    value = state.get_param(param_name)
    return ActionNodeOutput(output_text=value if isinstance(value, str) else "")


def create_scan_fixture(root: Path) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "nested").mkdir(parents=True)
    (root / "bin").mkdir(parents=True)

    (root / "alpha.txt").write_text("alpha")
    (root / "README").write_text("readme")
    (root / "docs" / "beta.py").write_text("print('beta')")
    (root / "docs" / "nested" / "gamma.md").write_text("# gamma")
    (root / "bin" / "delta.TXT").write_text("delta")


def file_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def expected_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for file in sorted(path for path in root.rglob("*") if path.is_file()):
        rows.append(
            {
                "Path": file.resolve().as_posix(),
                "MD5": file_md5(file),
                "Created": datetime.fromtimestamp(file.stat().st_ctime, tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
                "Modified": datetime.fromtimestamp(file.stat().st_mtime, tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return rows


def build_workflow(scan_root: Path) -> dict[str, object]:
    return {
        "schema_version": "1",
        "flow_id": "adr006-e2e-scan",
        "start_node_id": "INIT",
        "nodes": [
            {
                "id": "INIT",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "adr006_seed_scan_queue",
                    "function_parameters": {
                        "root_path": scan_root.as_posix(),
                        "queue_param_name": "scan_queue",
                        "rows_param_name": "table_rows",
                    },
                },
                "transitions": [{"next": "POP_NEXT"}],
            },
            {
                "id": "POP_NEXT",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "set_param_from_deque",
                    "function_parameters": {
                        "deque_param_name": "scan_queue",
                        "param_name": "cur_path",
                        "on_empty": "empty",
                        "on_set": "has_item",
                    },
                },
                "transitions": [
                    {"validator": {"equals": "empty"}, "next": "WRITE_TABLE_ARTIFACT"},
                    {"next": "EMIT_CUR_PATH"},
                ],
            },
            {
                "id": "EMIT_CUR_PATH",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "adr006_emit_param",
                    "function_parameters": {"param_name": "cur_path"},
                },
                "transitions": [
                    {"validator": {"function_name": "is_output_exist_file"}, "next": "COLLECT_FILE_INFO"},
                    {"next": "ENQUEUE_FOLDER"},
                ],
            },
            {
                "id": "COLLECT_FILE_INFO",
                "action_type": "functions",
                "action_parameters": {
                    "save_to_list": "table_rows",
                    "functions": {
                        "Path": {
                            "function_name": "adr006_pass_path",
                            "function_parameters": {"file_path": "param.cur_path"},
                        },
                        "MD5": {
                            "function_name": "md5_check_sum_file",
                            "function_parameters": {"file_path": "param.cur_path"},
                        },
                        "Created": {
                            "function_name": "file_create_time",
                            "function_parameters": {"file_path": "param.cur_path"},
                        },
                        "Modified": {
                            "function_name": "file_modify_time",
                            "function_parameters": {"file_path": "param.cur_path"},
                        },
                    },
                },
                "transitions": [{"next": "POP_NEXT"}],
            },
            {
                "id": "ENQUEUE_FOLDER",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "adr006_enqueue_folder_entries",
                    "function_parameters": {
                        "folder_path": "param.cur_path",
                        "queue_param_name": "scan_queue",
                    },
                },
                "transitions": [{"next": "POP_NEXT"}],
            },
            {
                "id": "WRITE_TABLE_ARTIFACT",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "dict_list_to_pretty_table",
                    "function_parameters": {
                        "artifact_name": "file_scan_table",
                        "dict_param_name": "table_rows",
                        "artifact_path": "reports/file_scan_table.csv",
                        "table_format": "csv",
                    },
                },
                "transitions": [{"stop": True}],
            },
        ],
    }


def test_adr006_recursive_scan_generates_artifact_table(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan-root"
    create_scan_fixture(scan_root)
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(build_workflow(scan_root), indent=2))

    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_path)
    response, state = engine.start_workflow(session_id)

    assert response.title == "Loop finished"
    assert state is not None

    rows = state.get_param("table_rows", list)
    assert isinstance(rows, list)
    assert sorted(rows, key=lambda row: row["Path"]) == sorted(expected_rows(scan_root), key=lambda row: row["Path"])

    artifact = state.artifacts["file_scan_table"]
    assert artifact.relative_path == Path("reports/file_scan_table.csv")
    artifact_file = state.work_dir / "artifacts" / artifact.relative_path
    assert artifact_file.is_file()
    content = artifact_file.read_text()
    assert "Path,MD5,Created,Modified" in content
    assert (scan_root / "docs" / "nested" / "gamma.md").resolve().as_posix() in content
    assert len(state.artifact_events) == 0
