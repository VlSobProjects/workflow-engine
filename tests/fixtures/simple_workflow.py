"""Portable replacement for the former `examples/simple_workflow.json` fixture.

The flow keeps the node shape the engine tests assert: `NODE_1` copies a file and stores the copy in a
parameter, its guard sees the copy on disk and therefore skips `NODE_2`, and `NODE_3` copies the stored
path once more. Every path is built under `tmp_path`, so the run depends on no machine-specific file.
"""

import json
from pathlib import Path

FIXTURE_DIRECTORY = "simple-workflow-fixture"
SOURCE_FILE_NAME = "report.txt"
WORKFLOW_FILE_NAME = "simple_workflow.json"


def build_simple_workflow(root: Path) -> dict:
    """Build the workflow definition for a fixture tree rooted at `root`."""
    source_path = root / "source" / SOURCE_FILE_NAME
    first_copy = root / "copy1" / SOURCE_FILE_NAME
    second_copy = root / "copy2" / SOURCE_FILE_NAME
    third_copy = root / "copy3" / SOURCE_FILE_NAME
    return {
        "schema_version": "1",
        "flow_id": "simple-workflow",
        "start_node_id": "NODE_1",
        "nodes": [
            {
                "id": "NODE_1",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "copy_file",
                    "function_parameters": {
                        "path_source": source_path.as_posix(),
                        "path_target": first_copy.as_posix(),
                    },
                },
                "save_as": "test_file_copy",
                "transitions": [
                    {
                        "next": "NODE_2",
                        "validator": {
                            "reversed": True,
                            "function_name": "is_file_exist",
                            "function_parameters": {"file_path": first_copy.as_posix()},
                        },
                    },
                    {"next": "NODE_3"},
                ],
                "validators": [{"function_name": "is_output_exist_file"}],
            },
            {
                "id": "NODE_2",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "copy_file",
                    "function_parameters": {
                        "path_source": "param.test_file_copy",
                        "path_target": second_copy.as_posix(),
                    },
                },
                "validators": [{"function_name": "is_output_exist_file"}],
            },
            {
                "id": "NODE_3",
                "action_type": "function",
                "action_parameters": {
                    "function_name": "copy_file",
                    "function_parameters": {
                        "path_source": "param.test_file_copy",
                        "path_target": third_copy.as_posix(),
                    },
                },
                "validators": [{"function_name": "is_output_exist_file"}],
            },
        ],
    }


def write_simple_workflow(tmp_path: Path) -> Path:
    """Create the source file the flow copies and write the workflow definition next to it."""
    root = tmp_path / FIXTURE_DIRECTORY
    source_path = root / "source" / SOURCE_FILE_NAME
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("simple workflow fixture", encoding="utf-8")

    workflow_path = root / WORKFLOW_FILE_NAME
    workflow_path.write_text(json.dumps(build_simple_workflow(root), indent=2), encoding="utf-8")
    return workflow_path
