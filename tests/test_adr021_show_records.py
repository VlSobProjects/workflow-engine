"""The read surface of the trail: `show-records` in the ADR 018 §3 discipline. See ADR 021 §4.

The stream is published as persisted, whole without flags; `--node` filters first and `--tail` bounds
last, and the answer says how many records it carries out of how many the stream holds.
"""

import json
from typing import cast

import pytest

from tests.test_adr021_record_writing import (
    CAPPED_LOOP,
    LINEAR_FLOW,
    build_workspace,
    run_json_cli,
    session_id_of,
    start,
)
from workflow_engine.cli.main import main


@pytest.fixture
def workspace(tmp_path):
    return build_workspace(tmp_path, LINEAR_FLOW)


@pytest.fixture
def session_id(workspace, capsys):
    code, response = start(workspace, capsys)
    assert code == 0, response
    return session_id_of(response)


def run_text_cli(argv: list[str], capsys) -> tuple[int, str]:
    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    return cast(int, exc_info.value.code), capsys.readouterr().out


def data_of(response: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], response["data"])


def show(workspace, session_id: str, capsys, *extra: str) -> tuple[int, dict[str, object]]:
    return run_json_cli(["show-records", "--session-id", session_id, "--config", workspace["config"], *extra], capsys)


class TestWholeStream:
    def test_without_flags_the_whole_stream_is_returned(self, workspace, session_id, capsys):
        code, response = show(workspace, session_id, capsys)

        assert code == 0
        data = data_of(response)
        assert data["count"] == 4
        assert data["total"] == 4
        assert [record["node_id"] for record in cast(list, data["records"])] == ["INIT", "GREET", "WRITE", "DONE"]

    def test_a_record_is_published_as_persisted(self, workspace, session_id, capsys):
        _, response = show(workspace, session_id, capsys)

        first = cast(list, data_of(response)["records"])[0]

        assert set(cast(dict, first)) == {
            "record_id",
            "timestamp",
            "node_id",
            "visit",
            "attempt",
            "action",
            "function",
            "status",
            "error_code",
            "guards",
            "transition",
            "writes",
            "artifacts",
            "details",
        }

    def test_the_answer_reports_where_the_run_stands_without_moving_it(self, workspace, session_id, capsys):
        code, response = show(workspace, session_id, capsys)

        assert code == 0
        assert response["workflow_status"] == "completed"
        assert response["event_code"] == "workflow_completed"
        assert response["command_status"] == "completed"

    def test_the_records_name_values_but_never_carry_them(self, workspace, session_id, capsys):
        _, response = show(workspace, session_id, capsys)

        published = json.dumps(data_of(response)["records"])

        assert "greeting" in published
        assert "hello" not in published


class TestBounds:
    def test_tail_bounds_the_answer_and_the_total_still_reports_the_whole(self, workspace, session_id, capsys):
        code, response = show(workspace, session_id, capsys, "--tail", "2")

        assert code == 0
        data = data_of(response)
        assert data["count"] == 2
        assert data["total"] == 4
        assert [record["node_id"] for record in cast(list, data["records"])] == ["WRITE", "DONE"]

    def test_node_filters_to_the_records_of_that_node(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, CAPPED_LOOP)
        _, response = start(workspace, capsys)
        session_id = session_id_of(response)

        _, filtered = show(workspace, session_id, capsys, "--node", "LOOP")

        data = data_of(filtered)
        assert data["total"] == 7
        assert [record["visit"] for record in cast(list, data["records"])] == [1, 2, 3, 4]

    def test_the_filter_runs_before_the_bound_so_the_two_compose(self, tmp_path, capsys):
        workspace = build_workspace(tmp_path, CAPPED_LOOP)
        _, response = start(workspace, capsys)
        session_id = session_id_of(response)

        _, filtered = show(workspace, session_id, capsys, "--node", "LOOP")
        _, both = show(workspace, session_id, capsys, "--node", "LOOP", "--tail", "1")

        assert data_of(both)["records"] == cast(list, data_of(filtered)["records"])[-1:]
        assert data_of(both)["total"] == 7

    def test_a_non_positive_tail_is_a_command_error(self, workspace, session_id, capsys):
        """`--tail 0` would answer with nothing at all, which reads as an empty stream."""
        code, response = show(workspace, session_id, capsys, "--tail", "0")

        assert code == 4
        assert response["command_status"] == "error"

    def test_a_session_whose_run_wrote_nothing_reads_as_an_empty_stream(self, workspace, capsys):
        code, created = run_json_cli(
            [
                "init-new-session",
                "--workflow-file",
                workspace["workflow"],
                "--config",
                workspace["config"],
            ],
            capsys,
        )
        assert code == 0, created

        _, response = show(workspace, session_id_of(created), capsys)

        assert data_of(response)["records"] == []
        assert data_of(response)["total"] == 0


class TestOperatorForm:
    def test_the_text_form_carries_one_line_per_record(self, workspace, session_id, capsys):
        code, output = run_text_cli(
            ["show-records", "--session-id", session_id, "--tail", "1", "--config", workspace["config"]], capsys
        )

        assert code == 0
        assert f"Records of session {session_id} (1 of 4 records):" in output
        assert "DONE visit 1 attempt 1  stop:echo_value  completed  -> end" in output

    def test_the_text_form_names_the_writes_and_the_artifacts_of_a_visit(self, workspace, session_id, capsys):
        _, output = run_text_cli(["show-records", "--session-id", session_id, "--config", workspace["config"]], capsys)

        assert "writes: greeting (builtins.str, SAVE_AS)" in output
        assert "artifacts: greeting_file" in output

    def test_an_unknown_session_is_a_command_error(self, workspace, capsys):
        code, response = show(workspace, "no-such-session", capsys)

        assert code == 4
        assert response["command_status"] == "error"
