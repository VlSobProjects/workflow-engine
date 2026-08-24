"""The `llm` action: its node contract, how it reads a reply, and what it fails under. See ADR 014 §1, §4, §5.

Every call here goes through an adapter that answers inside the process, so the action is measured
without a network: the `fake` adapter of the core for the scripted replies and the error classes, and
two adapters defined in this module for the two things `fake` deliberately does not do - report token
counts, and break the contract by raising.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest

import workflow_engine.codecs.base_codecs  # noqa: F401 - registers the codecs the declarations resolve
from workflow_engine.actions.action_llm import (
    LLM_ANSWER_INVALID,
    LLM_RECORD_FAILED,
    PROVIDER_FAILED,
    LlmAction,
)
from workflow_engine.actions.action_present import AnswerContract
from workflow_engine.actions.base_actions import ExecutionMode
from workflow_engine.answers import bind_answer, parse_answer
from workflow_engine.exceptions import (
    ActionConfigurationError,
    WorkflowAnswerError,
    WorkflowConfigurationError,
    WorkflowRuntimeError,
)
from workflow_engine.models.state import StateModel, StateReadOnlyView
from workflow_engine.models.workflow import validate_input_declarations
from workflow_engine.providers.base_provider import (
    BaseProvider,
    ProviderCall,
    ProviderErrorClass,
    ProviderReply,
    ProviderSettings,
    ProviderUsage,
)
from workflow_engine.providers.fake_provider import FakeProvider  # noqa: F401 - registers the `fake` adapter
from workflow_engine.providers.provider_seat import install_provider_settings
from workflow_engine.registry.action_registry import create_action, get_metadata_for_action
from workflow_engine.registry.provider_registry import register_provider

NODE_ID = "ASK_MODEL"


def _state(tmp_path: Path, node_id: str = NODE_ID) -> StateReadOnlyView:
    state = StateModel(
        timestamp=datetime.now(tz=UTC),
        work_dir=tmp_path,
        schema_version="1",
        flow_id="f",
        current_node_id=node_id,
        session_id="s",
    )
    state.add_parameter("topic", "storage costs")
    state.outputs["PREVIOUS"] = "42 rows"
    return StateReadOnlyView.from_state(state)


def _seat(name: str = "local", adapter: str = "fake", model: str | None = "small-1", **options) -> None:
    install_provider_settings(
        {name: ProviderSettings(name=name, adapter=adapter, model=model, options=MappingProxyType(dict(options)))}
    )


def _llm(**parameters) -> LlmAction:
    return LlmAction({"provider": "local", "prompt": "Summarize", "answer": [], **parameters})


class TestRegistration:
    def test_the_action_is_registered_as_automatic(self):
        action = create_action("llm", {"provider": "local", "prompt": "Summarize", "answer": []})

        assert isinstance(action, LlmAction)
        assert action.execution_mode() is ExecutionMode.AUTOMATIC

    def test_it_carries_operator_metadata_naming_the_provider_and_the_answer(self):
        metadata = get_metadata_for_action("llm")

        assert metadata is not None
        assert {"provider", "prompt", "answer"} == set(metadata.required_parameters)
        assert {"model", "format", "options", "record"} == set(metadata.optional_parameters)
        assert metadata.examples


class TestConfiguration:
    def test_the_answer_declaration_is_required(self):
        with pytest.raises(ActionConfigurationError):
            LlmAction({"provider": "local", "prompt": "Summarize"})

    def test_an_empty_declaration_calls_without_binding_anything(self):
        assert _llm().declarations == ()

    def test_the_default_format_is_text(self):
        assert _llm().format == "text"

    def test_a_format_outside_the_two_is_refused(self):
        with pytest.raises(ActionConfigurationError, match="format"):
            _llm(format="yaml")

    def test_the_text_format_binds_at_most_one_declared_name(self):
        with pytest.raises(ActionConfigurationError, match="binds at most one"):
            _llm(answer=[{"name": "category"}, {"name": "confidence"}])

    def test_the_json_format_takes_as_many_names_as_it_declares(self):
        action = _llm(format="json", answer=[{"name": "category"}, {"name": "confidence"}])

        assert [item.name for item in action.declarations] == ["category", "confidence"]

    def test_a_malformed_prompt_template_is_a_configuration_error_of_the_node(self):
        with pytest.raises(ActionConfigurationError, match="prompt"):
            _llm(prompt="Summarize $topic")

    def test_call_options_default_to_nothing(self):
        assert _llm().options == {}


class TestTheCall:
    def test_the_prompt_is_resolved_against_the_state_before_the_call(self, tmp_path, provider_seat_guard):
        _seat()
        action = _llm(prompt="Summarize ${param.topic} from ${output.PREVIOUS}")

        output = action.execute(_state(tmp_path), None)

        # The `fake` adapter answers with the prompt when nothing is scripted.
        assert output.output_text == "Summarize storage costs from 42 rows"
        assert output.error_code is None

    def test_an_unresolved_reference_fails_the_run_and_is_not_routable(self, tmp_path, provider_seat_guard):
        _seat()
        action = _llm(prompt="Summarize ${param.missing}")

        with pytest.raises(WorkflowRuntimeError):
            action.execute(_state(tmp_path), None)

    def test_the_node_model_wins_over_the_configured_default(self, tmp_path, provider_seat_guard):
        _seat(model="small-1")

        assert _llm(model="large-9").execute(_state(tmp_path), None).details["model"] == "large-9"

    def test_the_configured_model_answers_a_node_that_names_none(self, tmp_path, provider_seat_guard):
        _seat(model="small-1")

        assert _llm().execute(_state(tmp_path), None).details["model"] == "small-1"

    def test_a_call_with_no_model_anywhere_is_a_configuration_error(self, tmp_path, provider_seat_guard):
        _seat(model=None)

        with pytest.raises(WorkflowConfigurationError, match="without a model"):
            _llm().execute(_state(tmp_path), None)

    def test_a_provider_the_installation_does_not_configure_is_a_configuration_error(
        self, tmp_path, provider_seat_guard
    ):
        _seat(name="cloud")

        with pytest.raises(WorkflowConfigurationError, match="not configured"):
            _llm().execute(_state(tmp_path), None)

    def test_call_options_reach_the_adapter_unread(self, tmp_path, provider_seat_guard):
        _seat()
        action = _llm(options={"reply": "scripted by the option", "temperature": 0})

        assert action.execute(_state(tmp_path), None).output_text == "scripted by the option"


class TestReadingTheReply:
    def test_the_text_format_binds_the_whole_reply_to_the_declared_name(self, tmp_path, provider_seat_guard):
        _seat(replies=["a short summary"])
        action = _llm(answer=[{"name": "summary"}])

        output = action.execute(_state(tmp_path), None)

        assert output.get_param("summary") == "a short summary"
        assert output.output_text == "a short summary"

    def test_an_empty_declaration_binds_nothing_and_keeps_the_reply_as_the_output_text(
        self, tmp_path, provider_seat_guard
    ):
        _seat(replies=["a short summary"])

        output = _llm().execute(_state(tmp_path), None)

        assert output.param_writes == {}
        assert output.output_text == "a short summary"

    def test_the_json_format_binds_every_declared_name_through_its_codec(self, tmp_path, provider_seat_guard):
        _seat(replies=['{"category": "invoice", "pages": 12}'])
        action = _llm(format="json", answer=[{"name": "category"}, {"name": "pages", "type": "int"}])

        output = action.execute(_state(tmp_path), None)

        assert output.get_param("category") == "invoice"
        assert output.get_param("pages") == 12
        assert output.error_code is None

    def test_an_optional_name_the_reply_omits_is_not_bound(self, tmp_path, provider_seat_guard):
        _seat(replies=['{"category": "invoice"}'])
        action = _llm(
            format="json", answer=[{"name": "category"}, {"name": "confidence", "type": "float", "required": False}]
        )

        assert set(_names(action.execute(_state(tmp_path), None))) == {"category"}

    @pytest.mark.parametrize(
        "reply",
        [
            "not json at all",
            "[1, 2, 3]",
            '{"category": "invoice", "unexpected": 1}',
            "{}",
        ],
        ids=["unparsable", "not an object", "undeclared name", "missing required name"],
    )
    def test_a_reply_that_does_not_fit_the_declaration_is_a_routable_error(self, tmp_path, provider_seat_guard, reply):
        _seat(replies=[reply])
        action = _llm(format="json", answer=[{"name": "category"}])

        output = action.execute(_state(tmp_path), None)

        assert output.error_code == LLM_ANSWER_INVALID
        assert output.param_writes == {}

    def test_a_value_the_codec_cannot_decode_is_a_routable_error(self, tmp_path, provider_seat_guard):
        _seat(replies=['{"pages": "many"}'])
        action = _llm(format="json", answer=[{"name": "pages", "type": "int"}])

        assert action.execute(_state(tmp_path), None).error_code == LLM_ANSWER_INVALID

    def test_the_raw_reply_stays_the_output_text_of_a_refused_reply(self, tmp_path, provider_seat_guard):
        _seat(replies=["not json at all"])
        action = _llm(format="json", answer=[{"name": "category"}])

        assert action.execute(_state(tmp_path), None).output_text == "not json at all"


class TestFailureClasses:
    @pytest.mark.parametrize("error_class", list(ProviderErrorClass))
    def test_every_provider_error_class_is_the_error_code_of_the_node(self, tmp_path, provider_seat_guard, error_class):
        _seat(replies=[{"error": error_class.value, "message": "the provider refused"}])

        output = _llm().execute(_state(tmp_path), None)

        assert output.error_code == error_class.value
        assert output.error_msg == "the provider refused"
        assert output.output_text == ""

    def test_an_adapter_that_raises_fails_the_node_apart_from_the_six_classes(self, tmp_path, provider_seat_guard):
        _register_raising_adapter()
        _seat(adapter="raising")

        output = _llm().execute(_state(tmp_path), None)

        assert output.error_code == PROVIDER_FAILED
        assert "RuntimeError" in (output.error_msg or "")


class TestTheCallAudit:
    def test_an_answered_call_accounts_for_itself_in_the_details_of_the_output(self, tmp_path, provider_seat_guard):
        _seat(replies=["a short summary"])

        details = _llm().execute(_state(tmp_path), None).details

        assert details["provider"] == "local"
        assert details["model"] == "small-1"
        assert details["status"] == "answered"
        assert "error_class" not in details

    def test_a_failed_call_carries_its_class_in_the_details(self, tmp_path, provider_seat_guard):
        _seat(replies=[{"error": "rate_limited", "message": "slow down"}])

        details = _llm().execute(_state(tmp_path), None).details

        assert details["status"] == "failed"
        assert details["error_class"] == "rate_limited"

    def test_a_refused_reply_is_still_an_answered_call(self, tmp_path, provider_seat_guard):
        _seat(replies=["not json at all"])
        action = _llm(format="json", answer=[{"name": "category"}])

        assert action.execute(_state(tmp_path), None).details["status"] == "answered"

    def test_the_token_counts_an_adapter_reports_travel_with_the_call(self, tmp_path, provider_seat_guard):
        _register_counting_adapter()
        _seat(adapter="counting")

        details = _llm().execute(_state(tmp_path), None).details

        assert details["usage"] == {"prompt_tokens": 11, "completion_tokens": 7}

    def test_no_value_of_the_call_reaches_the_details(self, tmp_path, provider_seat_guard):
        _seat(replies=['{"category": "invoice"}'])
        action = _llm(format="json", answer=[{"name": "category"}])

        details = action.execute(_state(tmp_path), None).details

        assert "invoice" not in str(details)
        assert set(details) == {"provider", "model", "status"}


class TestTheAuditArtifacts:
    def test_the_prompt_and_the_reply_are_written_when_the_node_opts_in(self, tmp_path, provider_seat_guard):
        _seat(replies=["a short summary"])
        action = _llm(prompt="Summarize ${param.topic}", record=True)

        output = action.execute(_state(tmp_path), None)

        assert set(output.artifacts) == {f"{NODE_ID}.prompt.1.1", f"{NODE_ID}.reply.1.1"}
        assert _artifact_text(tmp_path, output, f"{NODE_ID}.prompt.1.1") == "Summarize storage costs"
        assert _artifact_text(tmp_path, output, f"{NODE_ID}.reply.1.1") == "a short summary"

    def test_nothing_is_written_when_the_node_does_not_opt_in(self, tmp_path, provider_seat_guard):
        _seat(replies=["a short summary"])

        assert _llm().execute(_state(tmp_path), None).artifacts == {}

    def test_a_failed_call_leaves_the_prompt_it_sent(self, tmp_path, provider_seat_guard):
        _seat(replies=[{"error": "timeout", "message": "no answer"}])

        output = _llm(record=True).execute(_state(tmp_path), None)

        assert set(output.artifacts) == {f"{NODE_ID}.prompt.1.1"}

    def test_an_audit_that_cannot_be_written_fails_the_node_under_its_own_code(
        self, tmp_path, provider_seat_guard, monkeypatch
    ):
        _seat(replies=["a short summary"])
        monkeypatch.setattr(Path, "open", _refuse_to_open)

        output = _llm(record=True).execute(_state(tmp_path), None)

        assert output.error_code == LLM_RECORD_FAILED
        assert output.output_text == "a short summary"


DECLARATION = [{"name": "category"}, {"name": "pages", "type": "int"}]
VALUES = {"category": "invoice", "pages": 12}


class TestOneDecodingPathWithTheAnswerBinding:
    """The same declaration binds the same way from an answer and from a reply. See ADR 014 §1."""

    def test_a_reply_and_an_answer_produce_the_same_writes(self, tmp_path, provider_seat_guard):
        _seat(replies=[json.dumps(VALUES)])
        action = _llm(format="json", answer=DECLARATION)

        from_reply = action.execute(_state(tmp_path), None).param_writes
        from_answer = bind_answer(
            parse_answer(json.dumps({"status": "success", "values": VALUES})),
            AnswerContract(declarations=validate_input_declarations(DECLARATION, "answer")),
        ).output.param_writes

        assert from_reply == from_answer

    def test_both_refuse_the_same_value_for_the_same_reason(self, tmp_path, provider_seat_guard):
        broken = {"category": "invoice", "pages": "many"}
        _seat(replies=[json.dumps(broken)])
        action = _llm(format="json", answer=DECLARATION)

        refusal = action.execute(_state(tmp_path), None)

        assert refusal.error_code == LLM_ANSWER_INVALID
        assert "pages" in (refusal.error_msg or "")
        with pytest.raises(WorkflowAnswerError, match="pages"):
            bind_answer(
                parse_answer(json.dumps({"status": "success", "values": broken})),
                AnswerContract(declarations=validate_input_declarations(DECLARATION, "answer")),
            )

    def test_the_refusal_names_the_transport_it_read(self, tmp_path, provider_seat_guard):
        _seat(replies=['{"category": "invoice"}'])
        action = _llm(format="json", answer=DECLARATION)

        assert "reply" in (action.execute(_state(tmp_path), None).error_msg or "")


def _names(output) -> list[str]:
    return list(output.param_writes)


def _artifact_text(tmp_path: Path, output, name: str) -> str:
    return (tmp_path / "artifacts" / output.artifacts[name].relative_path).read_text(encoding="utf-8")


def _refuse_to_open(*args, **kwargs):
    raise OSError("the artifacts directory is read-only")


def _register_raising_adapter() -> None:
    @register_provider("An adapter that breaks the contract by raising.", provider_type="raising")
    class RaisingProvider(BaseProvider):
        def complete(self, call: ProviderCall) -> ProviderReply:
            raise RuntimeError("the socket is gone")


def _register_counting_adapter() -> None:
    @register_provider("An adapter that reports what the call cost.", provider_type="counting")
    class CountingProvider(BaseProvider):
        def complete(self, call: ProviderCall) -> ProviderReply:
            return ProviderReply.answer(
                "counted",
                model=self.resolve_model(call.model),
                usage=ProviderUsage(prompt_tokens=11, completion_tokens=7),
            )
