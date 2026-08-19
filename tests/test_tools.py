"""The one rule for rendering a state value as text: a path renders in POSIX form. See ADR 008."""

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
    assert render_value_as_text(["a", "b"]) == "['a', 'b']"
