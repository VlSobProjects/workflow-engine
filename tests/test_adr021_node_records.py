"""The node record and the two operations the persistence contract gained for it. See ADR 021 §1-2."""

import json

import pytest

from workflow_engine.exceptions import StateLoadError, StateLoadParameterError
from workflow_engine.models.node_record import (
    NodeRecord,
    ParamWriteRecord,
    RecordPage,
    TransitionRecord,
)
from workflow_engine.models.state import GuardRecord
from workflow_engine.storage.json_storage import RECORDS_FILE, JsonStorage

SESSION_ID = "records_session"


def make_record(node_id: str = "scan", visit: int = 1, **overrides) -> NodeRecord:
    fields: dict[str, object] = {
        "node_id": node_id,
        "action": "function",
        "function": "file_size",
        "status": "completed",
        "transition": TransitionRecord.to_node("report"),
        "visit": visit,
        "attempt": 0,
    }
    fields.update(overrides)
    return NodeRecord(**fields)


@pytest.fixture
def storage(tmp_path) -> JsonStorage:
    return JsonStorage(tmp_path)


def test_record_round_trips_through_its_dict_form():
    record = make_record(
        guards=[GuardRecord(name="no_error", passed=True), GuardRecord(name="is_file", passed=False)],
        writes=[ParamWriteRecord(name="total_size", codec="int", mode="SET")],
        artifacts=["file_scan_table"],
        details={"llm": {"model": "some-model"}},
    )

    assert NodeRecord.from_dict(record.to_dict()) == record


def test_a_record_carries_names_and_codec_names_but_no_value():
    record = make_record(writes=[ParamWriteRecord(name="total_size", codec="int", mode="SET")])

    serialized = json.dumps(record.to_dict())

    assert "total_size" in serialized
    assert "value" not in serialized


def test_transition_kinds_carry_their_target():
    assert TransitionRecord.to_node("report").to_dict() == {"kind": "node", "target": "report"}
    assert TransitionRecord.to_end().to_dict() == {"kind": "end", "target": None}
    assert TransitionRecord.to_failure("no_transition_matched").to_dict() == {
        "kind": "fail",
        "target": "no_transition_matched",
    }


def test_an_unknown_status_is_refused_when_a_record_is_read_back():
    data = make_record().to_dict()
    data["status"] = "paused"

    with pytest.raises(StateLoadParameterError):
        NodeRecord.from_dict(data)


def test_an_unknown_transition_kind_is_refused_when_a_record_is_read_back():
    data = make_record().to_dict()
    data["transition"] = {"kind": "jump", "target": "report"}

    with pytest.raises(StateLoadParameterError):
        NodeRecord.from_dict(data)


def test_a_session_with_no_stream_reads_as_an_empty_page(storage):
    assert storage.load_records(SESSION_ID) == RecordPage(records=[], total=0)


def test_appended_records_are_read_back_in_the_order_they_were_written(storage):
    first, second = make_record(visit=1), make_record(visit=2)

    storage.append_record(SESSION_ID, first)
    storage.append_record(SESSION_ID, second)

    page = storage.load_records(SESSION_ID)
    assert [record.visit for record in page.records] == [1, 2]
    assert page.total == 2


def test_an_append_adds_a_line_and_touches_no_record_already_written(storage):
    storage.append_record(SESSION_ID, make_record(visit=1))
    records_file = storage.storage_dir / SESSION_ID / RECORDS_FILE
    first_line = records_file.read_text(encoding="utf-8").splitlines()[0]

    storage.append_record(SESSION_ID, make_record(visit=2))

    lines = records_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == first_line


def test_the_node_filter_selects_one_node_while_the_total_stays_the_whole_stream(storage):
    storage.append_record(SESSION_ID, make_record(node_id="scan"))
    storage.append_record(SESSION_ID, make_record(node_id="report"))
    storage.append_record(SESSION_ID, make_record(node_id="scan"))

    page = storage.load_records(SESSION_ID, node_id="scan")

    assert [record.node_id for record in page.records] == ["scan", "scan"]
    assert page.total == 3


def test_the_tail_keeps_the_last_records_and_reports_what_the_stream_holds(storage):
    for visit in (1, 2, 3):
        storage.append_record(SESSION_ID, make_record(visit=visit))

    page = storage.load_records(SESSION_ID, tail=2)

    assert [record.visit for record in page.records] == [2, 3]
    assert page.total == 3


def test_the_filter_runs_before_the_bound_so_the_two_compose(storage):
    storage.append_record(SESSION_ID, make_record(node_id="scan", visit=1))
    storage.append_record(SESSION_ID, make_record(node_id="report", visit=1))
    storage.append_record(SESSION_ID, make_record(node_id="scan", visit=2))
    storage.append_record(SESSION_ID, make_record(node_id="scan", visit=3))

    page = storage.load_records(SESSION_ID, node_id="scan", tail=2)

    assert [(record.node_id, record.visit) for record in page.records] == [("scan", 2), ("scan", 3)]
    assert page.total == 4


def test_a_tail_larger_than_the_stream_returns_the_stream(storage):
    storage.append_record(SESSION_ID, make_record(visit=1))

    page = storage.load_records(SESSION_ID, tail=10)

    assert len(page.records) == 1
    assert page.total == 1


def test_a_damaged_line_is_reported_rather_than_read_as_a_shorter_history(storage):
    storage.append_record(SESSION_ID, make_record(visit=1))
    records_file = storage.storage_dir / SESSION_ID / RECORDS_FILE
    with records_file.open("a", encoding="utf-8") as handle:
        handle.write("{not json" + chr(10))

    with pytest.raises(StateLoadError, match="line 2"):
        storage.load_records(SESSION_ID)


def test_a_record_with_non_ascii_text_survives_the_round_trip_on_disk(storage):
    storage.append_record(SESSION_ID, make_record(node_id="café", details={"note": "a naïve résumé"}))

    page = storage.load_records(SESSION_ID)

    assert page.records[0].node_id == "café"
    assert page.records[0].details == {"note": "a naïve résumé"}


def test_two_sessions_keep_their_own_streams(storage):
    storage.append_record(SESSION_ID, make_record(node_id="scan"))
    storage.append_record("other_session", make_record(node_id="report"))

    assert [record.node_id for record in storage.load_records(SESSION_ID).records] == ["scan"]
    assert [record.node_id for record in storage.load_records("other_session").records] == ["report"]
