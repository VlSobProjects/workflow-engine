"""What the engine tells the seated adapters when a run ends. See ADR 014 §2.

No node calls a provider yet - the `llm` action is the next session - so these runs seat an adapter
directly and then read back what the end of the run reported to it.
"""

import json
from pathlib import Path

from workflow_engine.answers import Answer, AnswerStatus
from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import load_config_file
from workflow_engine.engine import WorkflowEngine
from workflow_engine.models.state import SessionEventCode
from workflow_engine.providers.base_provider import BaseProvider, FinalizeReason, ProviderCall, ProviderReply
from workflow_engine.providers.fake_provider import FakeProvider
from workflow_engine.providers.provider_seat import resolve_provider, seated_providers
from workflow_engine.registry.provider_registry import register_provider

COMPLETING_FLOW = {
    "schema_version": "1",
    "flow_id": "provider-finalization-completing",
    "start_node_id": "DONE",
    "nodes": [
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        }
    ],
}

FAILING_FLOW = {
    "schema_version": "1",
    "flow_id": "provider-finalization-failing",
    "start_node_id": "CHECK",
    "nodes": [
        {
            "id": "CHECK",
            "action_type": "function",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "nothing here"}},
            "validators": [{"function_name": "is_output_exist_file"}],
            "transitions": [{"next": "DONE"}],
        },
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        },
    ],
}

INTERACTIVE_FLOW = {
    "schema_version": "1",
    "flow_id": "provider-finalization-interactive",
    "start_node_id": "ASK",
    "nodes": [
        {
            "id": "ASK",
            "action_type": "ask",
            "action_parameters": {"title": "Say the word", "instruction": "Answer with anything.", "answer": []},
            "transitions": [{"next": "DONE"}],
        },
        {
            "id": "DONE",
            "action_type": "stop",
            "action_parameters": {"function_name": "echo_value", "function_parameters": {"value": "finished"}},
        },
    ],
}


def build_engine(tmp_path: Path, adapter: str = "fake") -> WorkflowEngine:
    config_path = tmp_path / "workflow_engine_config.json"
    config_path.write_text(
        json.dumps(
            {
                "work_dir": (tmp_path / "runtime").as_posix(),
                "storage": {},
                "providers": {"local": {"adapter": adapter}},
            }
        ),
        encoding="utf-8",
    )
    return Bootstrap(load_config_file(config_path, cwd=tmp_path)).build_engine()


def write_workflow(tmp_path: Path, workflow: dict[str, object]) -> Path:
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
    return workflow_path


def seated_fake(tmp_path: Path, workflow: dict[str, object]) -> tuple[WorkflowEngine, FakeProvider, str]:
    engine = build_engine(tmp_path)
    provider = resolve_provider("local")
    session_id = engine.init_new_session(workflow_path=write_workflow(tmp_path, workflow))
    return engine, provider, session_id


class TestTheOutcomeReachesTheAdapter:
    def test_a_completed_run_releases_the_adapters_it_seated(self, tmp_path, provider_seat_guard):
        engine, provider, session_id = seated_fake(tmp_path, COMPLETING_FLOW)

        _, state = engine.start_workflow(session_id=session_id)

        assert state.get_last_event_code() is SessionEventCode.WORKFLOW_COMPLETED
        assert provider.last_finalize_reason is FinalizeReason.COMPLETED
        assert seated_providers() == ()

    def test_a_failed_run_says_so(self, tmp_path, provider_seat_guard):
        engine, provider, session_id = seated_fake(tmp_path, FAILING_FLOW)

        engine.start_workflow(session_id=session_id)

        assert provider.last_finalize_reason is FinalizeReason.FAILED

    def test_a_run_that_stopped_at_a_question_is_paused_rather_than_ended(self, tmp_path, provider_seat_guard):
        engine, provider, session_id = seated_fake(tmp_path, INTERACTIVE_FLOW)

        engine.start_workflow(session_id=session_id)

        assert provider.last_finalize_reason is FinalizeReason.PAUSED

    def test_the_answered_run_releases_the_adapter_of_its_own_process(self, tmp_path, provider_seat_guard):
        engine, _, session_id = seated_fake(tmp_path, INTERACTIVE_FLOW)
        engine.start_workflow(session_id=session_id)
        resumed = resolve_provider("local")

        engine.start_workflow(
            session_id=session_id, answer=Answer(status=AnswerStatus.SUCCESS, text="ok", actor="agent:tester")
        )

        assert resumed.last_finalize_reason is FinalizeReason.COMPLETED


class TestAFailureToRelease:
    def test_is_reported_without_turning_a_completed_run_into_a_failed_one(self, tmp_path, provider_seat_guard):
        @register_provider(description="Fails to release.", provider_type="stuck")
        class Stuck(BaseProvider):
            def complete(self, provider_call: ProviderCall) -> ProviderReply:
                return ProviderReply.answer("")

            def finalize(self, reason: FinalizeReason) -> None:
                raise RuntimeError("the model server did not answer")

        engine = build_engine(tmp_path, adapter="stuck")
        resolve_provider("local")
        session_id = engine.init_new_session(workflow_path=write_workflow(tmp_path, COMPLETING_FLOW))

        response, state = engine.start_workflow(session_id=session_id)

        assert state.get_last_event_code() is SessionEventCode.WORKFLOW_COMPLETED
        assert response.errors["provider:local"] == "RuntimeError: the model server did not answer"
