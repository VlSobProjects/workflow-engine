"""The generic bus components the ADR 014 gate variants are built from.

Three of them are new - a membership check for routing, a reader that puts the text of a file on the
bus, and a splitter that fills a deque with the pieces of a text - and one is the accumulator of the
collection family, which had to learn to start over inside a loop. None of them knows anything about
a model: what makes them ADR 014 work is only that the `described`, `tiered` and `chunked` variants
of the inventory example could not be expressed without them.
"""

from collections import deque
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.actions.modify_param_functions import (
    FILE_NOT_FOUND,
    FILE_NOT_TEXT,
    INVALID_CHUNK_SIZE,
    SPLIT_NO_TEXT,
    SPLIT_NOT_TEXT,
    init_list_param,
    read_text_file,
    split_text_to_deque,
)
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.validators.output_function_validators import is_output_in_collection


@pytest.fixture(autouse=True, scope="module")
def _components_registered(tmp_path_factory):
    create_engine(tmp_path_factory.mktemp("registration"))


class TestMembershipOfAListedCollection:
    def test_a_member_of_the_collection_holds(self):
        assert is_output_in_collection("text/plain", ["text/markdown", "text/plain"]) is True

    def test_a_value_the_collection_does_not_list_does_not_hold(self):
        assert is_output_in_collection("image/png", ["text/markdown", "text/plain"]) is False

    def test_an_empty_collection_never_holds(self):
        assert is_output_in_collection("text/plain", []) is False

    def test_a_member_is_compared_as_the_text_of_its_value(self):
        """The one rendering rule of ADR 008: a path is its POSIX form wherever it is compared."""

        assert is_output_in_collection("a/b/c.txt", [Path("a") / "b" / "c.txt"]) is True

    def test_a_single_string_is_one_member_and_not_its_letters(self):
        assert is_output_in_collection("t", "text/plain") is False
        assert is_output_in_collection("text/plain", "text/plain") is True

    def test_a_deque_is_looked_in_like_any_other_collection(self):
        assert is_output_in_collection("text/plain", deque(["text/plain"])) is True


class TestReadingATextFileOntoTheBus:
    def test_the_text_of_the_file_becomes_the_parameter(self, tmp_path: Path):
        source = tmp_path / "note.txt"
        source.write_text("first line\nsecond line\n", encoding="utf-8")

        output = read_text_file(source, "file_text")

        assert output.error_code is None
        assert output.output_text == "file_text"
        write = output.param_writes["file_text"]
        assert (write.mode, write.value) == (WriteParamMode.SET, "first line\nsecond line\n")

    def test_the_parameter_is_overwritten_because_the_node_lives_in_a_loop(self, tmp_path: Path):
        source = tmp_path / "note.txt"
        source.write_text("text", encoding="utf-8")

        assert read_text_file(source, "file_text").param_writes["file_text"].allow_overwrite is True

    def test_a_file_that_does_not_exist_is_a_routable_error(self, tmp_path: Path):
        output = read_text_file(tmp_path / "absent.txt", "file_text")

        assert output.error_code == FILE_NOT_FOUND
        assert output.param_writes == {}

    def test_a_file_that_does_not_decode_is_a_routable_error(self, tmp_path: Path):
        source = tmp_path / "picture.bin"
        source.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x81\x82")

        output = read_text_file(source, "file_text")

        assert output.error_code == FILE_NOT_TEXT
        assert output.param_writes == {}

    def test_an_encoding_no_installation_knows_is_a_routable_error(self, tmp_path: Path):
        source = tmp_path / "note.txt"
        source.write_text("text", encoding="utf-8")

        assert read_text_file(source, "file_text", encoding="not-an-encoding").error_code == FILE_NOT_TEXT

    def test_an_empty_file_is_read_as_an_empty_text(self, tmp_path: Path):
        source = tmp_path / "empty.txt"
        source.write_text("", encoding="utf-8")

        output = read_text_file(source, "file_text")

        assert output.error_code is None
        assert output.param_writes["file_text"].value == ""


class TestSplittingATextIntoChunks:
    def test_a_text_within_the_budget_is_one_chunk(self):
        output = split_text_to_deque("one paragraph", "chunk_queue", 100)

        assert output.error_code is None
        assert output.output_text == "1"
        assert output.param_writes["chunk_queue"].value == deque(["one paragraph"])

    def test_the_chunks_are_in_a_deque_front_first_and_rebuild_the_text(self):
        text = "\n".join(f"line {index}" for index in range(40))

        output = split_text_to_deque(text, "chunk_queue", 60)

        chunks = output.param_writes["chunk_queue"].value
        assert isinstance(chunks, deque)
        assert len(chunks) > 1
        assert "".join(chunks) == text
        assert output.output_text == str(len(chunks))

    def test_no_chunk_is_larger_than_the_budget(self):
        text = "\n".join(f"line {index}" for index in range(40))

        chunks = split_text_to_deque(text, "chunk_queue", 60).param_writes["chunk_queue"].value

        assert all(len(chunk) <= 60 for chunk in chunks)

    def test_a_chunk_ends_on_a_line_boundary_where_one_fits(self):
        text = "".join(f"line {index}\n" for index in range(10))

        chunks = split_text_to_deque(text, "chunk_queue", 30).param_writes["chunk_queue"].value

        assert all(chunk.endswith("\n") for chunk in chunks)

    def test_a_text_carrying_no_boundary_is_cut_on_the_budget(self):
        chunks = split_text_to_deque("x" * 25, "chunk_queue", 10).param_writes["chunk_queue"].value

        assert list(chunks) == ["x" * 10, "x" * 10, "x" * 5]

    def test_a_chunk_of_nothing_but_whitespace_is_never_sent_to_a_model(self):
        chunks = split_text_to_deque("head\n\n\n\n\n\n\n\n\n\n\n\n\n\ntail", "chunk_queue", 6)
        values = chunks.param_writes["chunk_queue"].value

        assert all(chunk.strip() for chunk in values)
        assert "".join(values) != ""

    def test_the_parameter_is_overwritten_because_the_node_lives_in_a_loop(self):
        assert split_text_to_deque("text", "chunk_queue", 10).param_writes["chunk_queue"].allow_overwrite is True

    @pytest.mark.parametrize("chunk_size", [0, -1])
    def test_a_budget_below_one_character_is_a_routable_error(self, chunk_size: int):
        output = split_text_to_deque("text", "chunk_queue", chunk_size)

        assert output.error_code == INVALID_CHUNK_SIZE
        assert output.param_writes == {}

    def test_a_value_that_is_not_text_is_a_routable_error(self):
        assert split_text_to_deque(["a", "b"], "chunk_queue", 10).error_code == SPLIT_NOT_TEXT

    @pytest.mark.parametrize("text", ["", "   \n\n  \t "])
    def test_a_text_with_nothing_in_it_is_a_routable_error(self, text: str):
        output = split_text_to_deque(text, "chunk_queue", 10)

        assert output.error_code == SPLIT_NO_TEXT
        assert output.param_writes == {}


class TestStartingAnAccumulatorOver:
    def test_the_accumulator_refuses_to_overwrite_by_default(self):
        assert init_list_param("part_descriptions").param_writes["part_descriptions"].allow_overwrite is False

    def test_a_loop_may_ask_for_a_fresh_accumulation(self):
        write = init_list_param("part_descriptions", allow_overwrite=True).param_writes["part_descriptions"]

        assert (write.mode, write.value, write.allow_overwrite) == (WriteParamMode.SET, [], True)
