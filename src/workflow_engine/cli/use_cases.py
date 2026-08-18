from argparse import Namespace
from datetime import datetime
from pathlib import Path

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import load_config_file
from workflow_engine.cli.contract import CommandName, CommandResult, CommandStatus
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.help_contract.builder import (
    ExternalNames,
    build_component_type_payload,
    build_components_payload,
    collect_help_components,
    external_names_from_report,
    find_help_component,
)
from workflow_engine.help_contract.models import COMPONENT_TYPE_BY_KEY, CONTRACT_VERSION
from workflow_engine.help_contract.renderers import (
    TextComponentRenderer,
    render_component_type_text,
    render_components_list_text,
)
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, ParamWrite, WorkflowArtifact


def _get_config(args: Namespace):
    config_path = getattr(args, "config", None)
    return load_config_file(
        None if config_path is None else Path(config_path),
        cwd=Path.cwd(),
        work_dir_override=getattr(args, "work_dir", None),
        storage_dir_override=getattr(args, "storage_dir", None),
    )


def _get_engine(args: Namespace):
    bootstrap = Bootstrap(_get_config(args))
    return bootstrap.build_engine()


def _get_artifacts(args: Namespace) -> dict[str, WorkflowArtifact]:
    artifacts = {}
    if args.artifact_name is not None and args.artifact_path is not None:
        artifacts[args.artifact_name] = WorkflowArtifact(
            relative_path=Path(args.artifact_path), created_at=datetime.now(), description=args.artifact_description
        )
    return artifacts


def _get_parameters(args: Namespace) -> dict[str, ParamWrite]:
    parameters = {}
    if args.param_name is not None and args.param_value is not None and args.write_mode is not None:
        write_mode = (
            WriteParamMode(args.write_mode)
            if any(mode for mode in WriteParamMode if mode.name == args.write_mode)
            else None
        )
        if args.param_name is not None and args.param_value is not None and write_mode is not None:
            parameters[args.param_name] = ParamWrite(value=args.param_value, mode=write_mode)
    return parameters


def _output_node(args: Namespace) -> ActionNodeOutput | None:
    if args.input is not None or args.error_code is not None:
        return ActionNodeOutput(
            output_text=getattr(args, "input", ""),
            error_code=getattr(args, "error_code", None),
            error_msg=getattr(args, "error_msg", None),
            param_writes=_get_parameters(args),
            artifacts=_get_artifacts(args),
        )
    return None


def init_session(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    session_id = engine.init_new_session(workflow_path=Path(args.workflow_file))
    if args.max_nodes_visited is not None:
        engine.set_session_limits(session_id=session_id, max_nodes_visited=args.max_nodes_visited)
    return CommandResult(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        message=f"Session {session_id} initialized for workflow {args.workflow_file}",
        data={"session_id": session_id, "workflow_path": args.workflow_file},
    )


def run_workflow(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    session_id = engine.init_new_session(workflow_path=Path(args.workflow_file))
    res, state = engine.start_workflow(session_id=session_id, export_dir=getattr(args, "export_dir", None))
    result = CommandResult.from_state(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        state=StateReadOnlyView.from_state(state),
        message=res.description,
    )
    result.data["deliverables"] = engine.get_deliverables(session_id)
    return result


def resume_workflow(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    session_id = args.session_id
    res, state = engine.start_workflow(
        session_id=session_id, output=_output_node(args), export_dir=getattr(args, "export_dir", None)
    )
    result = CommandResult.from_state(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        state=StateReadOnlyView.from_state(state),
        message=res.description,
    )
    result.data["deliverables"] = engine.get_deliverables(session_id)
    return result


def export_artifact(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    target_dir = Path(args.target_dir)
    exported = engine.export_artifact(
        session_id=args.session_id,
        target_dir=target_dir,
        artifact_name=args.artifact_name,
        all_deliverables=args.all,
    )
    return CommandResult(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        session_id=args.session_id,
        message=f"Exported {len(exported)} artifact(s) to {target_dir.as_posix()}",
        data={"exported": {item.logical_name: item.target_path for item in exported}},
    )


def set_limit(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    session_id = args.session_id
    state = engine.set_session_limits(session_id=session_id, max_nodes_visited=args.limit)
    message = f"Limit set to {args.limit} for session {session_id}"
    if args.limit == 0:
        message += (
            f"; no soft limit, but the run is still bounded by the global hard safety cap "
            f"hard_max_nodes_visited={engine.hard_max_nodes_visited}"
        )
    return CommandResult.from_state(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        state=state,
        message=message,
    )


def show_state(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    session_id = args.session_id
    state = engine.get_status(session_id=session_id)
    result = CommandResult.from_state_full(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        state=state,
        message=f"State for session {session_id}",
    )
    result.data["deliverables"] = engine.get_deliverables(session_id)
    return result


def list_of_sessions(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    sessions = engine.session_factory.get_all_sessions()
    return CommandResult(command=command_name, command_status=CommandStatus.COMPLETED, data={"sessions": sessions})


def help_components(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    external = external_names_from_report(engine.components)
    if args.json:
        return CommandResult(
            command=command_name,
            command_status=CommandStatus.COMPLETED,
            data=build_components_payload(external),
        )
    return CommandResult(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        message=render_components_list_text(collect_help_components(external)),
        data=None,
    )


def _help_component_type(command_name: CommandName, args: Namespace, external: ExternalNames) -> CommandResult:
    """The type-level mode of ``help-component``: the type description and its component list."""
    if args.json:
        return CommandResult(
            command=command_name,
            command_status=CommandStatus.COMPLETED,
            data=build_component_type_payload(args.component_type, external),
        )
    component_type = COMPONENT_TYPE_BY_KEY[args.component_type]
    components = collect_help_components(external)[component_type]
    return CommandResult(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        message=render_component_type_text(component_type, components),
        data=None,
    )


def help_component(command_name: CommandName, args: Namespace) -> CommandResult:
    engine = _get_engine(args)
    external = external_names_from_report(engine.components)
    if args.component_name is None:
        return _help_component_type(command_name, args, external)
    component = find_help_component(args.component_type, args.component_name, external)
    if component is None:
        return CommandResult(
            command=command_name,
            command_status=CommandStatus.ERROR,
            message=f"Component '{args.component_name}' of type '{args.component_type}' is not registered",
            errors={"component": f"{args.component_type}/{args.component_name} not found"},
            data=None,
        )
    if args.json:
        return CommandResult(
            command=command_name,
            command_status=CommandStatus.COMPLETED,
            data={"contract_version": CONTRACT_VERSION, "component": component.to_payload()},
        )
    return CommandResult(
        command=command_name,
        command_status=CommandStatus.COMPLETED,
        message=TextComponentRenderer(component).render(),
        data=None,
    )
