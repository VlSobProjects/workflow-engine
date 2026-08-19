"""ADR 013: the answer document, its refusals, and the published question block."""

import json
from pathlib import Path

import pytest

from tests.test_adr006_e2e_scan import create_engine
from workflow_engine.actions.action_present import AnswerContract, PresentResponse
from workflow_engine.answers import (
    ANSWER_FAILED,
    UNSPECIFIED_ACTOR,
    Answer,
    AnswerStatus,
    bind_answer,
    load_answer,
    parse_answer,
    question_block,
)
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.exceptions import WorkflowAnswerError
from workflow_engine.models.workflow import InputDeclaration, validate_input_declarations


@pytest.fixture(autouse=True, scope="module")
def _codecs_registered(tmp_path_factory):
    # Building an engine runs the component loader, which registers the codecs a declared type resolves against.
    create_engine(tmp_path_factory.mktemp("codec-registration"))


def _contract(entries: list[dict], errors: dict[str, str] | None = None) -> AnswerContract:
    return AnswerContract(
        declarations=validate_input_declarations(entries, "answer"), error_catalogue=dict(errors or {})
    )


class TestParsing:
    def test_minimal_success_answer(self):
        answer = parse_answer('{"status": "success"}')
        assert answer == Answer(status=AnswerStatus.SUCCESS)
        assert answer.actor == UNSPECIFIED_ACTOR
        assert answer.text == ""

    def test_every_field_is_read(self):
        answer = parse_answer(
            json.dumps(
                {
                    "status": "success",
                    "values": {"decision": "yes"},
                    "text": "approved",
                    "message": "looks good",
                    "actor": "agent:reviewer",
                }
            )
        )
        assert answer.values == {"decision": "yes"}
        assert answer.text == "approved"
        assert answer.message == "looks good"
        assert answer.actor == "agent:reviewer"

    @pytest.mark.parametrize(
        "raw",
        [
            "not json",
            "[]",
            '{"status": "escalate"}',
            "{}",
            '{"status": "success", "value": {}}',
            '{"status": "success", "values": []}',
            '{"status": "success", "text": 7}',
            '{"status": "success", "actor": ""}',
            '{"status": "failure"}',
            '{"status": "success", "error_code": "boom"}',
            '{"status": "failure", "error_code": "boom", "values": {"a": 1}}',
        ],
    )
    def test_malformed_answers_are_refused(self, raw):
        with pytest.raises(WorkflowAnswerError):
            parse_answer(raw)


class TestTransport:
    def test_no_answer_is_not_an_error(self):
        assert load_answer(None, None) is None

    def test_file_transport_reads_the_same_document(self, tmp_path: Path):
        answer_file = tmp_path / "answer.json"
        answer_file.write_text('{"status": "success", "text": "ok"}', encoding="utf-8")
        assert load_answer(None, answer_file.as_posix()) == parse_answer('{"status": "success", "text": "ok"}')

    def test_both_transports_at_once_are_refused(self, tmp_path: Path):
        with pytest.raises(WorkflowAnswerError):
            load_answer('{"status": "success"}', (tmp_path / "answer.json").as_posix())

    def test_missing_file_is_refused(self, tmp_path: Path):
        with pytest.raises(WorkflowAnswerError):
            load_answer(None, (tmp_path / "absent.json").as_posix())


class TestBinding:
    def test_declared_values_become_set_writes(self):
        bound = bind_answer(
            parse_answer('{"status": "success", "values": {"reviewer": "vlad"}, "text": "approved"}'),
            _contract([{"name": "reviewer"}]),
        )
        assert bound.output.output_text == "approved"
        assert bound.output.error_code is None
        write = bound.output.param_writes["reviewer"]
        assert (write.mode, write.value) == (WriteParamMode.SET, "vlad")
        assert bound.codecs == {"reviewer": None}

    def test_overwriting_is_allowed_so_a_repeated_question_can_answer_again(self):
        bound = bind_answer(
            parse_answer('{"status": "success", "values": {"reviewer": "vlad"}}'), _contract([{"name": "reviewer"}])
        )
        assert bound.output.param_writes["reviewer"].allow_overwrite is True

    def test_a_declared_type_decodes_the_value_and_is_recorded(self):
        bound = bind_answer(
            parse_answer('{"status": "success", "values": {"depth": 3}}'),
            _contract([{"name": "depth", "type": "int"}]),
        )
        assert bound.output.param_writes["depth"].value == 3
        assert bound.codecs == {"depth": "builtins.int"}

    def test_an_optional_name_may_be_absent(self):
        bound = bind_answer(parse_answer('{"status": "success"}'), _contract([{"name": "note", "required": False}]))
        assert bound.output.param_writes == {}

    def test_a_value_the_codec_cannot_decode_is_refused(self):
        with pytest.raises(WorkflowAnswerError):
            bind_answer(
                parse_answer('{"status": "success", "values": {"depth": "deep"}}'),
                _contract([{"name": "depth", "type": "int"}]),
            )

    def test_undeclared_name_is_refused(self):
        with pytest.raises(WorkflowAnswerError):
            bind_answer(
                parse_answer('{"status": "success", "values": {"other": 1}}'), _contract([{"name": "reviewer"}])
            )

    def test_missing_required_name_is_refused(self):
        with pytest.raises(WorkflowAnswerError):
            bind_answer(parse_answer('{"status": "success"}'), _contract([{"name": "reviewer"}]))

    def test_failure_carries_a_declared_code_into_the_output(self):
        bound = bind_answer(
            parse_answer('{"status": "failure", "error_code": "unreadable", "message": "no access"}'),
            _contract([{"name": "reviewer"}], {"unreadable": "The file cannot be read."}),
        )
        assert (bound.output.error_code, bound.output.error_msg) == ("unreadable", "no access")
        assert bound.output.param_writes == {}
        assert bound.codecs == {}

    def test_the_generic_code_is_always_accepted(self):
        bound = bind_answer(parse_answer(json.dumps({"status": "failure", "error_code": ANSWER_FAILED})), _contract([]))
        assert bound.output.error_code == ANSWER_FAILED

    def test_a_code_outside_the_catalogue_is_refused(self):
        with pytest.raises(WorkflowAnswerError):
            bind_answer(parse_answer('{"status": "failure", "error_code": "invented"}'), _contract([]))

    def test_a_failure_does_not_need_the_required_names(self):
        bound = bind_answer(
            parse_answer(json.dumps({"status": "failure", "error_code": ANSWER_FAILED})),
            _contract([{"name": "reviewer"}]),
        )
        assert bound.output.error_code == ANSWER_FAILED


class TestQuestionBlock:
    def test_it_publishes_the_question_the_declaration_and_the_catalogue(self):
        response = PresentResponse(
            title="Approve",
            description="Waiting",
            instruction="Answer yes or no",
            options=["yes", "no"],
            answer=AnswerContract(
                declarations=(InputDeclaration(name="reviewer"),), error_catalogue={"unreadable": "no access"}
            ),
        )
        block = question_block("ASK", response)
        assert block["node_id"] == "ASK"
        assert block["instruction"] == "Answer yes or no"
        assert block["options"] == ["yes", "no"]
        assert block["answer"] == [InputDeclaration(name="reviewer").to_dict()]
        assert block["error_catalogue"] == {"unreadable": "no access"}
        assert block["generic_error_code"] == ANSWER_FAILED

    def test_unset_presentation_fields_are_absent_rather_than_null(self):
        block = question_block("ASK", PresentResponse(title="T", description="D", instruction="I"))
        assert "options" not in block
        assert "goal" not in block
        assert block["answer"] == []
