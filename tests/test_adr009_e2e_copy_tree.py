"""ADR 009 reusability scenario: recursive copy of a file tree with core components only.

Together with the recursive scan (`test_adr006_e2e_scan.py`) this is the second realistic workflow
scenario required by the ADR 009 generality policy for the core helpers promoted from the ADR 006
tests: `init_deque_param`, `init_list_param`, `echo_value` and `enqueue_folder_entries`. The tree is
walked breadth-first through one deque, every file is copied flat into an existing target folder
(`copy_file` with a folder target), and a copy report artifact records source, copy and checksum.
"""

import hashlib
import json
from pathlib import Path

from tests.test_adr006_e2e_scan import create_engine


def create_source_tree(root: Path) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "nested").mkdir(parents=True)
    (root / "bin").mkdir(parents=True)

    (root / "alpha.txt").write_text("alpha")
    (root / "readme.md").write_text("readme")
    (root / "docs" / "beta.py").write_text("print('beta')")
    (root / "docs" / "nested" / "gamma.md").write_text("# gamma")
    (root / "bin" / "delta.bin").write_bytes(b"\x00delta")


def file_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def source_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def build_workflow(source_root: Path, target_dir: Path) -> dict[str, object]:
    return {
        "schema_version": "1",
        "flow_id": "adr009-e2e-copy-tree",
        "start_node_id": "INIT_QUEUE",
        "nodes": [
            {
                "id": "INIT_QUEUE",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "init_deque_param",
                    "function_parameters": {
                        "param_name": "walk_queue",
                        "items": [source_root.resolve().as_posix()],
                    },
                },
                "transitions": [{"next": "INIT_ROWS"}],
            },
            {
                "id": "INIT_ROWS",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "init_list_param",
                    "function_parameters": {"param_name": "copy_rows"},
                },
                "transitions": [{"next": "POP_NEXT"}],
            },
            {
                "id": "POP_NEXT",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "set_param_from_deque",
                    "function_parameters": {
                        "deque_param_name": "walk_queue",
                        "param_name": "cur_path",
                        "on_empty": "empty",
                        "on_set": "has_item",
                    },
                },
                "transitions": [
                    {"validator": {"equals": "empty"}, "next": "WRITE_REPORT"},
                    {"next": "EMIT_CUR_PATH"},
                ],
            },
            {
                "id": "EMIT_CUR_PATH",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "echo_value",
                    "function_parameters": {"value": "param.cur_path"},
                },
                "transitions": [
                    {"validator": {"function_name": "is_output_exist_file"}, "next": "COPY_FILE"},
                    {"next": "ENQUEUE_FOLDER"},
                ],
            },
            {
                "id": "COPY_FILE",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "copy_file",
                    "function_parameters": {
                        "path_source": "param.cur_path",
                        "path_target": target_dir.resolve().as_posix(),
                    },
                },
                "save_as": "copied_path",
                "transitions": [{"next": "COLLECT_COPY_ROW"}],
            },
            {
                "id": "COLLECT_COPY_ROW",
                "action_type": "functions",
                "action_parameters": {
                    "save_to_list": "copy_rows",
                    "functions": {
                        "Source": {
                            "function_name": "echo_value",
                            "function_parameters": {"value": "param.cur_path"},
                        },
                        "Copied": {
                            "function_name": "echo_value",
                            "function_parameters": {"value": "param.copied_path"},
                        },
                        "MD5": {
                            "function_name": "md5_check_sum_file",
                            "function_parameters": {"file_path": "param.copied_path"},
                        },
                    },
                },
                "transitions": [{"next": "POP_NEXT"}],
            },
            {
                "id": "ENQUEUE_FOLDER",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "enqueue_folder_entries",
                    "function_parameters": {
                        "folder_path": "param.cur_path",
                        "deque_param_name": "walk_queue",
                    },
                },
                "transitions": [{"next": "POP_NEXT"}],
            },
            {
                "id": "WRITE_REPORT",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "dict_list_to_pretty_table",
                    "function_parameters": {
                        "artifact_name": "copy_report",
                        "dict_param_name": "copy_rows",
                        "artifact_path": "reports/copy_report.csv",
                        "table_format": "csv",
                    },
                },
                "transitions": [{"stop": True}],
            },
        ],
    }


def test_adr009_recursive_copy_flattens_tree_into_target(tmp_path: Path) -> None:
    source_root = tmp_path / "source-root"
    create_source_tree(source_root)
    target_dir = tmp_path / "copy-target"
    target_dir.mkdir()
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(build_workflow(source_root, target_dir), indent=2))

    engine = create_engine(tmp_path)
    session_id = engine.init_new_session(workflow_path)
    response, state = engine.start_workflow(session_id)

    assert response.title == "Loop finished"
    assert state is not None

    sources = source_files(source_root)
    copies = sorted(path for path in target_dir.iterdir() if path.is_file())
    assert [copy.name for copy in copies] == sorted(source.name for source in sources)
    for source in sources:
        assert file_md5(target_dir / source.name) == file_md5(source)

    rows = state.get_param("copy_rows", list)
    assert isinstance(rows, list)
    assert sorted(row["Source"] for row in rows) == [source.resolve().as_posix() for source in sources]
    for row in rows:
        assert row["Copied"] == (target_dir.resolve() / Path(row["Source"]).name).as_posix()
        assert row["MD5"] == file_md5(Path(row["Copied"]))

    artifact = state.artifacts["copy_report"]
    assert artifact.relative_path == Path("reports/copy_report.csv")
    artifact_file = state.work_dir / "artifacts" / artifact.relative_path
    assert artifact_file.is_file()
    content = artifact_file.read_text()
    assert "Source,Copied,MD5" in content
    for source in sources:
        assert (target_dir.resolve() / source.name).as_posix() in content
