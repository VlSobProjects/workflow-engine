"""Roadmap step 9: the hold the engine takes on a session, and what it refuses.

The engine is a single writer per session. These cases fix what that means in practice: a second
writer is refused by name while the first one works, a reader is never made to wait, and a call that
leaves by any path leaves the session free. The lock is exercised both directly and through the
engine, because the promise is the engine's and not the CLI's.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import WorkflowEngineConfiguration
from workflow_engine.bootstrap.session_lock import LOCK_FILE, SessionLock
from workflow_engine.cli.main import main
from workflow_engine.exceptions import SessionBusyError, WorkflowInputError, WorkflowRuntimeError
from workflow_engine.inputs import parse_input_assignment

TEMPLATE = Path(__file__).resolve().parents[1] / "examples" / "approve-and-copy.json"


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    return tmp_path / "runtime"


@pytest.fixture
def engine(work_dir: Path):
    return Bootstrap(WorkflowEngineConfiguration(work_dir=work_dir.as_posix())).build_engine()


@pytest.fixture
def session_id(engine) -> str:
    return engine.init_new_session(workflow_path=TEMPLATE)


@pytest.fixture
def lock_path(engine, session_id) -> Path:
    return engine.session_factory.session_dir(session_id) / LOCK_FILE


@pytest.fixture
def other_process(engine, session_id) -> SessionLock:
    """The hold of a second writer on the same session, taken through a lock of its own."""

    lock = SessionLock(session_id, engine.session_factory.session_dir(session_id))
    lock.acquire()
    return lock


class TestTheLockItself:
    def test_a_second_hold_on_the_same_session_is_refused(self, engine, session_id, other_process):
        second = SessionLock(session_id, engine.session_factory.session_dir(session_id))

        with pytest.raises(SessionBusyError):
            second.acquire()

    def test_the_refusal_names_the_holder_and_the_file(self, engine, session_id, other_process, lock_path):
        second = SessionLock(session_id, engine.session_factory.session_dir(session_id))

        with pytest.raises(SessionBusyError) as error:
            second.acquire()

        record = json.loads(lock_path.read_text(encoding="utf-8"))
        assert str(record["pid"]) in str(error.value)
        assert record["acquired_at"] in str(error.value)
        assert lock_path.as_posix() in str(error.value)

    def test_the_hold_is_re_entrant_for_its_owner(self, engine, session_id, lock_path):
        lock = SessionLock(session_id, engine.session_factory.session_dir(session_id))

        with lock:
            with lock:
                assert lock_path.is_file()
            # The inner hold ended, the outer one did not: the session is still taken.
            assert lock_path.is_file()
        assert not lock_path.exists()

    def test_releasing_a_hold_that_was_never_taken_does_nothing(self, engine, session_id, lock_path, other_process):
        stranger = SessionLock(session_id, engine.session_factory.session_dir(session_id))

        stranger.release()

        assert lock_path.is_file()


class TestMutatingCalls:
    """Every call that writes the state is refused while another writer holds the session."""

    def test_starting_a_run_is_refused(self, engine, session_id, other_process):
        with pytest.raises(SessionBusyError, match=session_id):
            engine.start_workflow(session_id=session_id)

    def test_binding_inputs_is_refused(self, engine, session_id, other_process, tmp_path):
        source = tmp_path / "source.txt"
        source.write_text("content")

        with pytest.raises(SessionBusyError, match=session_id):
            engine.set_inputs(
                session_id=session_id,
                assignments=[parse_input_assignment(f"source_file:Path={source.as_posix()}")],
            )

    def test_setting_a_limit_is_refused(self, engine, session_id, other_process):
        with pytest.raises(SessionBusyError, match=session_id):
            engine.set_session_limits(session_id=session_id, max_nodes_visited=10)

    def test_an_unknown_session_reads_as_a_missing_session(self, engine):
        """The lock is taken before the session is loaded, so it must not rename the usual failure."""

        with pytest.raises(WorkflowRuntimeError, match="not found at path"):
            engine.start_workflow(session_id="unknown-session-id")


class TestReadingCalls:
    """A reader of a held session is never blocked: it takes nothing. See `purpose.md`."""

    def test_the_read_surfaces_answer_while_the_session_is_held(self, engine, session_id, other_process):
        assert engine.get_status(session_id).session_id == session_id
        assert engine.get_records(session_id).total == 0
        assert engine.get_deliverables(session_id) == []
        assert [declaration["name"] for declaration in engine.get_inputs(session_id)]


class TestTheSessionIsLeftFree:
    def test_a_created_session_carries_no_lock(self, lock_path):
        assert not lock_path.exists()

    def test_a_refused_call_releases_the_session(self, engine, session_id, lock_path):
        # The template declares required inputs, so a run started without them fails on entry.
        with pytest.raises(WorkflowInputError):
            engine.start_workflow(session_id=session_id)

        assert not lock_path.exists()

    def test_a_completed_call_releases_the_session(self, engine, session_id, lock_path):
        engine.set_session_limits(session_id=session_id, max_nodes_visited=10)

        assert not lock_path.exists()


class TestThroughTheCommandLine:
    def test_a_held_session_is_reported_as_a_setup_error(
        self, work_dir, tmp_path, engine, session_id, other_process, capsys
    ):
        config_path = tmp_path / "workflow_engine_config.json"
        config_path.write_text(json.dumps({"work_dir": work_dir.as_posix(), "external_modules": [], "storage": {}}))

        with pytest.raises(SystemExit) as exit_info:
            main(["resume", "--session-id", session_id, "--config", config_path.as_posix(), "--json"])

        assert exit_info.value.code == 4
        response = cast(dict[str, object], json.loads(capsys.readouterr().out))
        message = cast(str, response["message"])
        assert session_id in message
        assert LOCK_FILE in message
