from datetime import datetime
from pathlib import Path

from argparse import Namespace

from workflow_engine.bootstrap.bootstrap import Bootstrap
from workflow_engine.bootstrap.config_loader import load_config_file
from workflow_engine.cli.contract import CommandResult, CommandStatus
from workflow_engine.cli.main import CommandName
from workflow_engine.collection_param_handlers import WriteParamMode
from workflow_engine.models.state import StateReadOnlyView
from workflow_engine.output import ActionNodeOutput, WorkflowArtifact, ParamWrite


# def _get_engine():

def _get_config(config_path: str | None):
    return load_config_file(None if config_path is None else Path(config_path))

def _get_engine(config_path: str | None = None):
    bootstrap = Bootstrap(_get_config(config_path))
    return bootstrap.build_engine()

def _get_artifacts(args:Namespace) ->dict[str,WorkflowArtifact]:
    artifacts = {}
    if getattr(args, "artifact_name") is not None and getattr(args, "artifact_path") is not None:
        if args.artifact_name is not None and args.artifact_path is not None:
            artifacts[args.artifact_name] = WorkflowArtifact(
                relative_path=Path(args.artifact_path), created_at=datetime.now(), description=args.artifact_description
            )
    return artifacts

def _get_parameters(args:Namespace) ->dict[str,ParamWrite]:
    parameters = {}
    if getattr(args, "param_name") is not None and getattr(args, "param_value") is not None and getattr(args, "write_mode") is not None:
        write_mode = WriteParamMode(args.write_mode) if any([mode for mode in WriteParamMode if mode.name == args.write_mode]) else None
        if args.param_name is not None and args.param_value is not None and write_mode is not None:
            parameters[args.param_name] = ParamWrite(value=args.param_value, mode=write_mode)
    return parameters

def _output_node(args:Namespace)-> ActionNodeOutput | None:
    if getattr(args, "input") is not None or getattr(args,"error_code") is not None:
        return ActionNodeOutput(
            output_text=getattr(args, "input",""),
            error_code=getattr(args, "error_code", None),
            error_msg=getattr(args, "error_msg", None),
            param_writes=_get_parameters(args),
            artifacts=_get_artifacts(args)
        )
    return None

def init_session(command_name:CommandName, args:Namespace) ->CommandResult:
    engine = _get_engine(args.config)
    session_id = engine.init_new_session(workflow_path=Path(args.workflow_file))
    if args.max_nodes_visited is not None:
        engine.set_session_limits(session_id=session_id, max_nodes_visited=args.max_nodes_visited)
    return CommandResult(
        command=command_name,
        status=CommandStatus.COMPLETED,
        message=f"Session {session_id} initialized for workflow {args.workflow_file}",
        data={"session_id": session_id, "workflow_path": args.workflow_file}
    )

def run_workflow(command_name:CommandName, args:Namespace) ->CommandResult:
    engine = _get_engine(args.config)
    session_id = engine.init_new_session(workflow_path=Path(args.workflow_file))
    res,state = engine.start_workflow(session_id=session_id)
    return CommandResult.from_state(
        command=command_name,
        status=CommandStatus.COMPLETED,
        state=StateReadOnlyView.from_state(state),
        message=res.description
    )

def resume_workflow(command_name:CommandName, args:Namespace) ->CommandResult:
    engine = _get_engine(args.config)
    session_id = args.session_id
    res,state = engine.start_workflow(session_id=session_id, output=_output_node(args))
    return CommandResult.from_state(
        command=command_name,
        status=CommandStatus.COMPLETED,
        state=StateReadOnlyView.from_state(state),
        message=res.description
    )

def set_limit(command_name:CommandName, args:Namespace) ->CommandResult:
    engine = _get_engine(args.config)
    session_id = args.session_id
    state = engine.set_session_limits(session_id=session_id, max_nodes_visited=args.limit)
    return CommandResult.from_state(
        command=command_name,
        status=CommandStatus.COMPLETED,
        state=state,
        message=f"Limit set to {args.limit} for session {session_id}"
    )

def show_state(command_name:CommandName, args:Namespace) ->CommandResult:
    engine = _get_engine(args.config)
    session_id = args.session_id
    state = engine.get_status(session_id=session_id)
    return CommandResult.from_state_full(
        command=command_name,
        status=CommandStatus.COMPLETED,
        state=state,
        message=f"Limit set to {args.limit} for session {session_id}"
    )

def list_of_sessions(command_name:CommandName, args:Namespace) ->CommandResult:
    engine = _get_engine(args.config)
    sessions = engine.session_factory.get_all_sessions()
    return CommandResult(
        command=command_name,
        status=CommandStatus.COMPLETED,
        data={"sessions": sessions}
    )

def help_components(command_name:CommandName, args:Namespace) ->CommandResult:
    engine = _get_engine(args.config)
    components = engine.components
    return CommandResult(
        command=command_name,
        status=CommandStatus.COMPLETED,
        data={"components": components}
    )

def help_component(command_name:CommandName, args:Namespace) ->CommandResult:
    return CommandResult(
        command=command_name,
        status=CommandStatus.COMPLETED,
        data={"component_type": args.component_type, "component_name": args.component_name}
    )

