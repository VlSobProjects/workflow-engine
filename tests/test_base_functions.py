import pytest

from workflow_engine.actions.base_functions import copy_file, copy_file_to_folder
from workflow_engine.exceptions import FunctionRuntimeError


@pytest.fixture
def source_file(tmp_path):
    source = tmp_path / "source" / "a.txt"
    source.parent.mkdir()
    source.write_text("AAA", encoding="utf-8")
    return source


def test_copy_file_copies_to_the_given_file_path(source_file, tmp_path):
    target = tmp_path / "copy.txt"

    result = copy_file(source_file.as_posix(), target.as_posix())

    assert result.error_code is None
    assert result.output_text == target.absolute().as_posix()
    assert target.read_text(encoding="utf-8") == "AAA"


def test_copy_file_refuses_an_existing_folder_as_target(source_file, tmp_path):
    target = tmp_path / "out"
    target.mkdir()

    result = copy_file(source_file.as_posix(), target.as_posix())

    assert result.error_code == "target_is_folder"
    assert "copy_file_to_folder" in result.error_msg
    assert list(target.iterdir()) == []


def test_copy_file_refuses_a_missing_target_folder(source_file, tmp_path):
    target = tmp_path / "missing" / "copy.txt"

    result = copy_file(source_file.as_posix(), target.as_posix())

    assert result.error_code == "target_folder_not_found"
    assert not target.parent.exists()


def test_copy_file_to_folder_copies_under_the_source_name(source_file, tmp_path):
    target_folder = tmp_path / "out"
    target_folder.mkdir()

    result = copy_file_to_folder(source_file.as_posix(), target_folder.as_posix())

    assert result.error_code is None
    assert result.output_text == (target_folder / "a.txt").absolute().as_posix()
    assert (target_folder / "a.txt").read_text(encoding="utf-8") == "AAA"


def test_copy_file_to_folder_refuses_a_missing_folder(source_file, tmp_path):
    target_folder = tmp_path / "out"

    result = copy_file_to_folder(source_file.as_posix(), target_folder.as_posix())

    assert result.error_code == "target_folder_not_found"
    assert not target_folder.exists()


def test_copying_several_files_into_one_folder_keeps_them_distinct(source_file, tmp_path):
    """The tree-copy regression: every source must land as its own file, not overwrite one target."""
    second = source_file.parent / "b.txt"
    second.write_text("BBB", encoding="utf-8")
    target_folder = tmp_path / "out"
    target_folder.mkdir()

    for source in (source_file, second):
        assert copy_file_to_folder(source.as_posix(), target_folder.as_posix()).error_code is None

    copies = sorted(path.name for path in target_folder.iterdir())
    assert copies == ["a.txt", "b.txt"]
    assert (target_folder / "a.txt").read_text(encoding="utf-8") == "AAA"
    assert (target_folder / "b.txt").read_text(encoding="utf-8") == "BBB"


@pytest.mark.parametrize("function", [copy_file, copy_file_to_folder])
def test_a_missing_source_fails_the_run(function, tmp_path):
    with pytest.raises(FunctionRuntimeError):
        function((tmp_path / "nowhere.txt").as_posix(), tmp_path.as_posix())
