import json
from typing import cast

from workflow_engine.cli.contract import CommandResult
from workflow_engine.tools import common_encoder, render_value_as_text


def command_result_encoder(obj):
    obj_common = common_encoder(obj)

    if obj_common is not None:
        return obj_common

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def render_text(response: CommandResult) -> str:
    command = response.command.value if response.command is not None else "unknown"
    resp_list = [f"Command: {command}", f"Status: {response.command_status.value}"]
    if response.workflow_status:
        resp_list.append(f"Workflow Status: {response.workflow_status.value}")
    if response.errors:
        resp_list.append(f"Errors: {response.errors}")
    if response.message:
        resp_list.append(f"Message: {response.message}")
    if response.data:
        resp_list.append(f"Data: {response.data}")
    return "\n".join(resp_list)


def render_json(response: CommandResult) -> str:
    return json.dumps(response.__dict__, indent=2, sort_keys=True, default=command_result_encoder)


def render_parameters_list_text(session_id: str, parameters: list[dict[str, str]]) -> str:
    """The operator form of `list-parameters`: one line per parameter, values never among them."""
    if not parameters:
        return f"No parameters in session {session_id}"
    lines = [f"Parameters of session {session_id} ({len(parameters)}):"]
    lines.extend(
        f"- {parameter['name']}: {parameter['type']} (written by {parameter['source_node']})"
        for parameter in parameters
    )
    return "\n".join(lines)


def render_journal_text(session_id: str, events: list[dict[str, object]], total: int) -> str:
    """The operator form of `show-journal`: one line per event, details in the state's own JSON form.

    The header names how many events the answer carries out of the whole journal, so a `--tail` or
    `--node` reader sees that the answer is bounded rather than mistaking it for the full record.
    """
    if not events:
        return f"No events to show in session {session_id} (journal holds {total})"
    lines = [f"Journal of session {session_id} ({len(events)} of {total} events):"]
    lines.extend(
        f"{event['timestamp']}  {event['actor']}  {event['code']}  {render_value_as_text(event['details'])}"
        for event in events
    )
    return "\n".join(lines)


def _record_transition_text(transition: dict[str, object]) -> str:
    target = transition.get("target")
    kind = str(transition.get("kind"))
    return kind if target is None else f"{kind} {target}"


def _record_line(record: dict[str, object]) -> str:
    action = str(record["action"])
    function = record.get("function")
    status = str(record["status"])
    error_code = record.get("error_code")
    parts = [
        str(record["timestamp"]),
        f"{record['node_id']} visit {record['visit']} attempt {record['attempt']}",
        action if function is None else f"{action}:{function}",
        status if error_code is None else f"{status} ({error_code})",
        f"-> {_record_transition_text(cast(dict, record['transition']))}",
    ]
    guards = cast(list, record.get("guards") or [])
    if guards:
        rendered = ", ".join(f"{guard['name']}={'pass' if guard['passed'] else 'fail'}" for guard in guards)
        parts.append(f"guards: {rendered}")
    writes = cast(list, record.get("writes") or [])
    if writes:
        rendered = ", ".join(f"{write['name']} ({write['codec']}, {write['mode']})" for write in writes)
        parts.append(f"writes: {rendered}")
    artifacts = cast(list, record.get("artifacts") or [])
    if artifacts:
        parts.append("artifacts: " + ", ".join(str(name) for name in artifacts))
    details = cast(dict, record.get("details") or {})
    if details:
        parts.append(f"details: {render_value_as_text(details)}")
    return "  ".join(parts)


def render_records_text(session_id: str, records: list[dict[str, object]], total: int) -> str:
    """The operator form of `show-records`: one line per concluded visit, names and never values.

    The header names how many records the answer carries out of the whole stream, so a `--tail` or
    `--node` reader sees that the answer is bounded rather than mistaking it for the full trail.
    """
    if not records:
        return f"No records to show in session {session_id} (stream holds {total})"
    lines = [f"Records of session {session_id} ({len(records)} of {total} records):"]
    lines.extend(_record_line(record) for record in records)
    return "\n".join(lines)
