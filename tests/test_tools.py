"""The one rule for rendering a state value as text: a path renders in POSIX form. See ADR 008."""

from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath

from workflow_engine.tools import render_value_as_text


def test_a_string_is_returned_unchanged():
    assert render_value_as_text("already text") == "already text"


def test_a_windows_path_renders_with_forward_slashes():
    # `str()` of this path is native and would disagree with every path the engine writes.
    assert render_value_as_text(PureWindowsPath(r"C:\tmp\some\file.txt")) == "C:/tmp/some/file.txt"


def test_a_posix_path_renders_unchanged():
    assert render_value_as_text(PurePosixPath("/tmp/some/file.txt")) == "/tmp/some/file.txt"


def test_any_other_value_renders_as_its_string_form():
    assert render_value_as_text(7) == "7"


def test_a_collection_renders_as_compact_json():
    # A published question and a guard comparison read the same form the state is written in, and a
    # Python repr is neither parseable nor the stored form. See ADR 016 §3.
    assert render_value_as_text(["a", "b"]) == '["a","b"]'
    assert render_value_as_text({"name": "report", "rows": 2}) == '{"name":"report","rows":2}'


def test_a_path_inside_a_collection_renders_in_posix_form():
    assert render_value_as_text([PureWindowsPath("C:/tmp/file.txt")]) == '["C:/tmp/file.txt"]'


def test_a_datetime_inside_a_collection_renders_in_iso_form():
    assert render_value_as_text([datetime(2026, 8, 20, 12, 0, tzinfo=UTC)]) == '["2026-08-20T12:00:00+00:00"]'


def test_a_value_no_encoder_knows_falls_back_to_its_text_form():
    # `common_encoder` returns None for what it does not know, and `json.dumps` would write that as
    # `null`; the scalar rule of this very function is the fallback instead.
    assert render_value_as_text([object.__new__(_Unencodable)]) == '["unencodable"]'


class _Unencodable:
    def __str__(self) -> str:
        return "unencodable"
