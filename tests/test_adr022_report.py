"""The human-readable report of one session: its fact model and the document around it. See ADR 022.

The viewer is JavaScript and is checked in a browser elsewhere; these tests cover the model in full —
read back from the data block of the written document, as the viewer reads it — and the document's
own guarantees: one file, nothing from outside, a block that cannot close its element early, and a
session left exactly as it was.
"""

import json
import re
from pathlib import Path
from typing import cast

import pytest

from tests.test_adr021_record_writing import CAPPED_LOOP, FAILING_FLOW, LINEAR_FLOW, run_json_cli
from workflow_engine.exceptions import (
    ActionConfigurationError,
    WorkflowConfigurationError,
    WorkflowParameterConfigurationError,
)
from workflow_engine.report import model as report_model
from workflow_engine.report.model import VALUE_CUT

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
INVENTORY = EXAMPLES_DIR / "folder-inventory-to-csv.json"
APPROVE_AND_COPY = EXAMPLES_DIR / "approve-and-copy.json"

_DATA_BLOCK = re.compile(r'<script type="application/json" id="report-data">(.*?)</script>', re.S)


def write_config(tmp_path: Path, **extra: object) -> str:
    path = tmp_path / "workflow_engine_config.json"
    path.write_text(
        json.dumps({"work_dir": (tmp_path / "runtime").as_posix(), "external_modules": [], "storage": {}, **extra})
    )
    return path.as_posix()


@pytest.fixture
def config(tmp_path: Path) -> str:
    return write_config(tmp_path)


@pytest.fixture
def home(tmp_path: Path, monkeypatch) -> Path:
    """The home directory of the machine writing the report, put where the test's paths live."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def create_tree(root: Path) -> Path:
    """Two files in the root and one in a nested folder, so the walk loops and recurses."""
    (root / "nested").mkdir(parents=True)
    (root / "first.txt").write_text("first")
    (root / "second.txt").write_text("second")
    (root / "nested" / "third.txt").write_text("third")
    return root


def write_flow(tmp_path: Path, flow: dict[str, object]) -> str:
    path = tmp_path / f"{flow['flow_id']}.json"
    path.write_text(json.dumps(flow))
    return path.as_posix()


def run(config: str, workflow: str, capsys, *inputs: str) -> tuple[int, str]:
    argv = ["run", "--workflow-file", workflow, "--config", config]
    for assignment in inputs:
        argv += ["--input", assignment]
    code, response = run_json_cli(argv, capsys)
    return code, cast(str, response["session_id"])


def report(config: str, session_id: str, capsys, *extra: str) -> tuple[int, dict[str, object]]:
    return run_json_cli(["report", "--session-id", session_id, "--config", config, *extra], capsys)


def data_of(response: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], response["data"])


def model_of(document: str) -> dict[str, object]:
    match = _DATA_BLOCK.search(document)
    assert match is not None
    return cast(dict[str, object], json.loads(match.group(1)))


def report_model_of(config: str, session_id: str, capsys, *extra: str) -> dict[str, object]:
    code, response = report(config, session_id, capsys, *extra)
    assert code == 0, response
    return model_of(Path(cast(str, data_of(response)["path"])).read_text(encoding="utf-8"))


def node_of(model: dict[str, object], node_id: str) -> dict[str, object]:
    nodes = cast(list[dict[str, object]], cast(dict[str, object], model["definition"])["nodes"])
    return next(node for node in nodes if node["id"] == node_id)


def parameter_of(model: dict[str, object], name: str) -> dict[str, object]:
    return next(p for p in cast(list[dict[str, object]], model["parameters"]) if p["name"] == name)


def path_of(model: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], model["path"])


@pytest.fixture
def completed(tmp_path, config, home, capsys) -> tuple[str, str]:
    tree = create_tree(tmp_path / "tree")
    code, session_id = run(config, INVENTORY.as_posix(), capsys, f"scan_root={tree.as_posix()}")
    assert code == 0
    return session_id, tree.as_posix()


class TestCompletedRunWithALoop:
    def test_the_model_holds_the_sections_the_viewer_reads(self, config, completed, capsys):
        model = report_model_of(config, completed[0], capsys)

        assert model["schema_version"] == "1"
        assert set(model) == {
            "schema_version",
            "generated_at",
            "options",
            "session",
            "definition",
            "path",
            "parameters",
            "artifacts",
            "journal",
            "pending",
        }
        session = cast(dict[str, object], model["session"])
        assert session["id"] == completed[0]
        assert session["flow_id"] == "folder-inventory-to-csv"
        assert session["ending"] == {"status": "completed", "event": "workflow_completed", "node_id": "WRITE_REPORT"}
        assert model["pending"] is None

    def test_the_path_is_every_record_in_order_with_the_transition_each_took(self, config, completed, capsys):
        path = path_of(report_model_of(config, completed[0], capsys))

        pops = [visit for visit in path if visit["node_id"] == "POP_NEXT"]
        assert [visit["visit"] for visit in pops] == list(range(1, len(pops) + 1))
        assert {visit["taken_origin"] for visit in pops[:-1]} == {"transitions[1]"}
        assert pops[-1]["taken_origin"] == "transitions[0]"
        assert pops[-1]["transition"] == {"kind": "node", "target": "WRITE_TABLE"}
        emits = {visit["taken_origin"] for visit in path if visit["node_id"] == "EMIT_CUR_PATH"}
        assert emits == {"transitions[0]", "transitions[1]"}
        assert path[-1]["node_id"] == "WRITE_REPORT"
        assert path[-1]["taken_origin"] == "transitions[1]"

    def test_a_node_carries_both_views(self, config, completed, capsys):
        node = node_of(report_model_of(config, completed[0], capsys), "WRITE_TABLE")

        written = cast(dict[str, object], node["written"])
        assert written["id"] == "WRITE_TABLE"
        assert written["transitions"] == [
            {"errors": ["pretty_table_no_data", "pretty_table_artifact_exists", "pretty_table_write_error"]},
            {"next": "WRITE_REPORT"},
        ]
        assert node["effective"] == [
            {
                "origin": "transitions[0]",
                "guard": "errors:pretty_table_no_data,pretty_table_artifact_exists,pretty_table_write_error",
                "attempts": False,
                "kind": "fail",
                "target": None,
            },
            {"origin": "transitions[1]", "guard": None, "attempts": False, "kind": "node", "target": "WRITE_REPORT"},
        ]
        assert node["build_error"] is None

    def test_the_workflow_input_is_marked_and_its_value_shows_the_home_as_tilde(self, config, completed, capsys):
        model = report_model_of(config, completed[0], capsys)

        scan_root = parameter_of(model, "scan_root")
        assert scan_root["is_input"] is True
        assert scan_root["value"] == "~/tree"
        assert parameter_of(model, "table_rows")["is_input"] is False
        assert cast(dict[str, object], model["options"])["home_replaced"] is True

    def test_a_long_value_is_cut_and_says_its_full_length(self, config, completed, capsys):
        rows = parameter_of(report_model_of(config, completed[0], capsys), "table_rows")

        assert rows["cut"] is True
        assert len(cast(str, rows["value"])) == VALUE_CUT
        assert cast(int, rows["length"]) > VALUE_CUT
        assert completed[1] not in cast(str, rows["value"])

    def test_without_values_no_value_is_written(self, config, completed, capsys):
        model = report_model_of(config, completed[0], capsys, "--no-values")

        assert cast(dict[str, object], model["options"])["values"] is False
        assert cast(dict[str, object], model["options"])["home_replaced"] is False
        assert {p["value"] for p in cast(list[dict[str, object]], model["parameters"])} == {None}

    def test_the_artifacts_are_named_by_path_in_the_session_and_marked_as_deliverables(self, config, completed, capsys):
        artifacts = report_model_of(config, completed[0], capsys)["artifacts"]

        assert artifacts == [
            {
                "name": "file_scan_report",
                "path": "reports/file_scan_report.txt",
                "description": "One table per folder, the folder path as its heading",
                "deliverable": True,
            },
            {
                "name": "file_scan_table",
                "path": "reports/file_scan_table.csv",
                "description": "Pretty table text from parameter: table_rows",
                "deliverable": True,
            },
        ]


class TestEndings:
    def test_a_failed_run_ends_under_its_code(self, tmp_path, config, capsys):
        (tmp_path / "empty").mkdir()
        code, session_id = run(config, INVENTORY.as_posix(), capsys, f"scan_root={(tmp_path / 'empty').as_posix()}")
        assert code == 3

        model = report_model_of(config, session_id, capsys)

        ending = cast(dict[str, object], cast(dict[str, object], model["session"])["ending"])
        assert ending == {
            "status": "failed",
            "event": "workflow_failed",
            "node_id": "WRITE_TABLE",
            "code": "pretty_table_no_data",
        }
        assert path_of(model)[-1]["taken_origin"] == "transitions[0]"
        assert model["pending"] is None

    def test_a_run_paused_on_its_budget_names_the_next_node_and_how_to_resume(self, tmp_path, config, capsys):
        tree = create_tree(tmp_path / "tree")
        _, init = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                INVENTORY.as_posix(),
                "--max-nodes-visited",
                "6",
                "--config",
                config,
            ],
            capsys,
        )
        session_id = cast(str, init["session_id"])
        run_json_cli(
            ["set-input", "--session-id", session_id, "--input", f"scan_root={tree.as_posix()}", "--config", config],
            capsys,
        )
        code, _ = run_json_cli(["resume", "--session-id", session_id, "--config", config], capsys)
        assert code == 2

        model = report_model_of(config, session_id, capsys)

        pending = cast(dict[str, object], model["pending"])
        assert pending["kind"] == "budget"
        assert pending["nodes_visited"] == 6
        assert pending["max_nodes_visited"] == 6
        ending = cast(dict[str, object], cast(dict[str, object], model["session"])["ending"])
        assert pending["node_id"] == ending["node_id"]
        assert f"set-limit --session-id {session_id}" in cast(str, pending["resume"])
        assert len(path_of(model)) == 6

    def test_a_run_paused_at_a_question_carries_the_question_as_written(self, tmp_path, config, home, capsys):
        source = tmp_path / "contract.txt"
        source.write_text("terms")
        (tmp_path / "target").mkdir()
        code, session_id = run(
            config,
            APPROVE_AND_COPY.as_posix(),
            capsys,
            f"source_file={source.as_posix()}",
            f"target_dir={(tmp_path / 'target').as_posix()}",
        )
        assert code == 2

        model = report_model_of(config, session_id, capsys)

        pending = cast(dict[str, object], model["pending"])
        assert pending["kind"] == "question"
        assert pending["node_id"] == "ASK_APPROVAL"
        presentation = cast(dict[str, str], pending["presentation"])
        assert "${param.source_file}" in presentation["instruction"]
        assert presentation["title"] == "Approve the copy"
        assert pending["lists"] == {"options": ["approved", "rejected"]}
        assert pending["answer"] == [{"name": "reviewer", "required": True, "description": "Who made the decision"}]
        assert pending["errors"] == {"source_unreadable": "The file cannot be read, so no decision can be made."}
        assert pending["generic_error_code"] == "answer_failed"
        resume = cast(str, pending["resume"])
        assert resume.startswith(f"workflow-engine resume --session-id {session_id} --answer '")
        assert json.loads(resume.split("--answer ", 1)[1].strip("'"))["values"] == {"reviewer": "<value>"}
        assert parameter_of(model, "source_file")["value"] == "~/contract.txt"

    def test_a_question_is_also_carried_as_it_was_presented(self, tmp_path, config, home, capsys):
        session_id = self._paused_at_question(tmp_path, config, capsys)

        pending = cast(dict[str, object], report_model_of(config, session_id, capsys)["pending"])

        presented = cast(dict[str, dict[str, object]], pending["presented"])
        instruction = cast(str, presented["fields"]["instruction"])
        assert "${" not in instruction
        assert instruction.startswith("Decide whether '~/contract.txt' (")
        assert presented["fields"]["title"] == "Approve the copy"
        assert presented["lists"] == {"options": ["approved", "rejected"]}
        assert pending["presented_error"] is None

    def test_without_values_the_question_is_carried_only_as_written(self, tmp_path, config, capsys):
        session_id = self._paused_at_question(tmp_path, config, capsys)

        pending = cast(dict[str, object], report_model_of(config, session_id, capsys, "--no-values")["pending"])

        assert pending["presented"] is None
        assert pending["presented_error"] is None
        assert "${param.source_file}" in cast(dict[str, str], pending["presentation"])["instruction"]

    def test_a_reference_that_no_longer_resolves_leaves_the_question_as_written(
        self, tmp_path, config, capsys, monkeypatch
    ):
        session_id = self._paused_at_question(tmp_path, config, capsys)

        def unresolved(state, text):
            raise WorkflowParameterConfigurationError("Parameter 'source_size' not found")

        monkeypatch.setattr(report_model, "resolve_template_text", unresolved)

        pending = cast(dict[str, object], report_model_of(config, session_id, capsys)["pending"])

        assert pending["presented"] is None
        assert "source_size" in cast(str, pending["presented_error"])

    @staticmethod
    def _paused_at_question(tmp_path: Path, config: str, capsys) -> str:
        source = tmp_path / "contract.txt"
        source.write_text("terms")
        (tmp_path / "target").mkdir()
        code, session_id = run(
            config,
            APPROVE_AND_COPY.as_posix(),
            capsys,
            f"source_file={source.as_posix()}",
            f"target_dir={(tmp_path / 'target').as_posix()}",
        )
        assert code == 2
        return session_id

    def test_a_run_paused_at_the_safety_cap_names_the_cap(self, tmp_path, capsys):
        config = write_config(tmp_path, hard_max_nodes_visited=7)
        loop = {**CAPPED_LOOP, "flow_id": "report-uncapped-loop", "nodes": [dict(n) for n in CAPPED_LOOP["nodes"]]}
        del loop["nodes"][0]["max_visits"]
        code, session_id = run(config, write_flow(tmp_path, loop), capsys)
        assert code == 2

        pending = cast(dict[str, object], report_model_of(config, session_id, capsys)["pending"])

        assert pending["kind"] == "safety"
        assert pending["hard_max_nodes_visited"] == 7

    def test_a_run_that_ended_with_no_outcome_is_interrupted_where_the_state_stands(self, tmp_path, config, capsys):
        _, session_id = run(config, write_flow(tmp_path, LINEAR_FLOW), capsys)
        # A process that ends mid-run leaves the entry event as the last one: drop what followed it.
        state_file = tmp_path / "runtime" / "json-storage" / session_id / "state.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert state["session_events"][-1]["code"] == "workflow_completed"
        state["session_events"].pop()
        state_file.write_text(json.dumps(state), encoding="utf-8")

        model = report_model_of(config, session_id, capsys)

        ending = cast(dict[str, object], cast(dict[str, object], model["session"])["ending"])
        assert ending == {"status": "paused", "event": "workflow_started", "node_id": "DONE", "interrupted": True}
        assert model["pending"] == {
            "kind": "interrupted",
            "node_id": "DONE",
            "resume": f"workflow-engine resume --session-id {session_id}",
        }

    def test_a_session_not_started_says_where_it_begins(self, tmp_path, config, capsys):
        _, init = run_json_cli(
            ["init-new-session", "--workflow-file", write_flow(tmp_path, LINEAR_FLOW), "--config", config], capsys
        )

        model = report_model_of(config, cast(str, init["session_id"]), capsys)

        assert model["pending"] == {
            "kind": "start",
            "node_id": "INIT",
            "resume": f"workflow-engine resume --session-id {init['session_id']}",
        }
        assert model["path"] == []


class TestOrigins:
    def test_a_failing_validator_is_the_transition_its_visit_took(self, tmp_path, config, capsys):
        code, session_id = run(config, write_flow(tmp_path, FAILING_FLOW), capsys)
        assert code == 3

        model = report_model_of(config, session_id, capsys)

        effective = cast(list[dict[str, object]], node_of(model, "CHECK")["effective"])
        assert [t["origin"] for t in effective] == ["validators[0]", "transitions[0]"]
        assert effective[0]["guard"] == "all_of(no_error, not is_output_exist_file)"
        assert effective[0]["kind"] == "fail"
        assert effective[0]["target"] == "is_output_exist_file"
        assert path_of(model)[0]["taken_origin"] == "validators[0]"

    def test_a_visit_refused_on_entry_took_no_transition(self, tmp_path, config, capsys):
        code, session_id = run(config, write_flow(tmp_path, CAPPED_LOOP), capsys)
        assert code == 3

        refused = path_of(report_model_of(config, session_id, capsys))[-1]

        assert refused["error_code"] == "max_visits_exceeded"
        assert refused["taken_origin"] is None

    def test_a_node_that_cannot_be_built_keeps_its_written_view_and_states_why(
        self, tmp_path, config, capsys, monkeypatch
    ):
        _, session_id = run(config, write_flow(tmp_path, LINEAR_FLOW), capsys)
        real_factory = report_model.workflow_node_factory

        def factory(node):
            if node.id == "GREET":
                cause = WorkflowConfigurationError("Function 'echo_value' is not registered")
                raise ActionConfigurationError("function", "exception in get_registered_function") from cause
            return real_factory(node)

        monkeypatch.setattr(report_model, "workflow_node_factory", factory)

        model = report_model_of(config, session_id, capsys)

        greet = node_of(model, "GREET")
        assert greet["build_error"] == (
            "Action configuration error in 'function': exception in get_registered_function; "
            "caused by: Function 'echo_value' is not registered"
        )
        assert greet["effective"] == [
            {"origin": "transitions[0]", "guard": None, "attempts": False, "kind": "node", "target": "WRITE"}
        ]
        assert cast(dict[str, object], greet["written"])["save_as"] == "greeting"
        assert node_of(model, "WRITE")["build_error"] is None


ESCAPING_FLOW = {
    "schema_version": "1",
    "flow_id": "report-escaping",
    "start_node_id": "SAY",
    "nodes": [
        {
            "id": "SAY",
            "action_type": "function",
            "action_parameters": {
                "function_name": "echo_value",
                "function_parameters": {"value": "</script><!-- <b>bold</b>"},
            },
            "save_as": "said",
            "transitions": [{"stop": True}],
        }
    ],
}


class TestDocument:
    def test_a_value_cannot_close_the_data_block(self, tmp_path, config, capsys):
        _, session_id = run(config, write_flow(tmp_path, ESCAPING_FLOW), capsys)

        _, response = report(config, session_id, capsys)
        document = Path(cast(str, data_of(response)["path"])).read_text(encoding="utf-8")

        assert "</script><!--" not in document
        assert document.count("</script>") == 2
        assert parameter_of(model_of(document), "said")["value"] == "</script><!-- <b>bold</b>"

    def test_the_document_carries_its_viewer_and_reaches_for_nothing_outside(self, config, completed, capsys):
        _, response = report(config, completed[0], capsys)
        document = Path(cast(str, data_of(response)["path"])).read_text(encoding="utf-8")

        assert document.startswith("<!doctype html>")
        assert 'id="report-data"' in document
        assert "const MODEL = JSON.parse" in document
        # Only one tab is shown at a time: the panels are hidden by the attribute, which the section's own
        # display rule would otherwise override and lay every tab out in one column.
        assert "[hidden] { display: none !important; }" in document
        assert "<script src" not in document
        assert "<link" not in document
        assert "http://" not in document
        assert "https://" not in document
        assert "<title>folder-inventory-to-csv · completed · workflow-engine report</title>" in document

    def test_the_report_is_written_into_the_session_directory_by_default(self, tmp_path, config, completed, capsys):
        code, response = report(config, completed[0], capsys)

        assert code == 0
        expected = tmp_path / "runtime" / "sessions" / completed[0] / "report.html"
        assert data_of(response)["path"] == expected.resolve().as_posix()
        assert expected.is_file()
        assert response["workflow_status"] == "completed"

    def test_output_writes_the_report_elsewhere(self, tmp_path, config, completed, capsys):
        target = tmp_path / "published" / "run.html"

        code, response = report(config, completed[0], capsys, "--output", target.as_posix())

        assert code == 0
        assert data_of(response)["path"] == target.resolve().as_posix()
        assert model_of(target.read_text(encoding="utf-8"))["session"]
        assert not (tmp_path / "runtime" / "sessions" / completed[0] / "report.html").exists()

    def test_writing_the_report_changes_nothing_of_the_session(self, tmp_path, config, completed, capsys):
        runtime = tmp_path / "runtime"

        def snapshot() -> dict[str, bytes]:
            return {
                path.relative_to(runtime).as_posix(): path.read_bytes()
                for path in sorted(runtime.rglob("*"))
                if path.is_file() and path.name != "report.html"
            }

        before = snapshot()
        report(config, completed[0], capsys)
        report(config, completed[0], capsys)

        assert snapshot() == before

    def test_an_unknown_session_is_a_command_error(self, config, capsys):
        code, response = report(config, "no-such-session", capsys)

        assert code == 4
        assert response["command_status"] == "error"
