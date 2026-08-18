import argparse
import sys
from argparse import Namespace
from collections.abc import Callable
from dataclasses import dataclass, field

from workflow_engine.cli.contract import CommandName, CommandResult, CommandStatus
from workflow_engine.cli.exit_codes import ExitCode, get_exit_code
from workflow_engine.cli.presenters import render_json, render_text
from workflow_engine.cli.use_cases import (
    help_component,
    help_components,
    init_session,
    list_of_sessions,
    resume_workflow,
    run_workflow,
    set_limit,
    show_state,
)
from workflow_engine.collection_param_handlers import WriteParamMode, get_all_modes_help
from workflow_engine.exceptions import WorkflowEngineError
from workflow_engine.help_contract.models import COMPONENT_TYPE_BY_KEY


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(f"Error: {message}")
        self.print_help()
        sys.exit(ExitCode.ERROR.value)


@dataclass
class CommandArgs:
    key: str
    help: str
    required: bool = field(default=True)
    type: type = field(default=str)
    action: str = field(default="store")
    choices: list[str] | None = field(default=None)
    choices_help: str | None = field(default=None)

    def add_argument(self, command: argparse.ArgumentParser):
        if self.choices is not None:
            command.add_argument(
                self.key,
                help=self.help,
                required=self.required,
                type=self.type,
                action=self.action,
                choices=self.choices,
            )
        else:
            command.add_argument(
                self.key,
                help=self.help,
                required=self.required,
                type=self.type,
                action=self.action,
            )


@dataclass
class Command:
    command: CommandName
    help: str
    runner: Callable[[CommandName, Namespace], CommandResult]
    args: list[CommandArgs] = field(default_factory=list)

    def add_to_parser(self, parser: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser):
        command_parser = parser.add_parser(self.command.value, help=self.help, parents=[shared_parser])
        for arg in self.args:
            arg.add_argument(command_parser)

    def run_command(self, args: Namespace) -> CommandResult:
        try:
            return self.runner(self.command, args)
        except WorkflowEngineError as e:
            return CommandResult(
                command=self.command,
                command_status=CommandStatus.ERROR,
                message=str(e),
                data=args.__dict__,
            )


def _session_id_arg() -> CommandArgs:
    return CommandArgs(
        key="--session-id",
        help="Session ID",
    )


def _get_commend(command_name: CommandName) -> Command:
    match command_name:
        case CommandName.INIT_NEW_SESSION:
            return Command(
                command=CommandName.INIT_NEW_SESSION,
                help="Initialize a new workflow session",
                runner=init_session,
                args=[
                    CommandArgs(
                        key="--workflow-file",
                        help="Path to the workflow file",
                    ),
                    CommandArgs(
                        key="--max-nodes-visited",
                        type=int,
                        help="Maximum number of nodes to visit in the workflow",
                        required=False,
                    ),
                ],
            )
        case CommandName.RUN:
            return Command(
                command=CommandName.RUN,
                help="Run a workflow",
                runner=run_workflow,
                args=[
                    CommandArgs(
                        key="--workflow-file",
                        help="Path to the workflow file",
                    )
                ],
            )
        case CommandName.RESUME:
            return Command(
                command=CommandName.RESUME,
                help="Resume a workflow",
                runner=resume_workflow,
                args=[
                    _session_id_arg(),
                    CommandArgs(key="--input", help="Input from operator to the workflow", required=False),
                    CommandArgs(key="--error-code", help="Error code from operator to the workflow", required=False),
                    CommandArgs(key="--error-msg", help="Error message from operator to the workflow", required=False),
                    CommandArgs(
                        key="--param-name", help="Parameter name from operator to the workflow", required=False
                    ),
                    CommandArgs(
                        key="--param-value", help="Parameter value from operator to the workflow", required=False
                    ),
                    CommandArgs(
                        key="--write-mode",
                        help="Write mode for the parameter",
                        required=False,
                        choices=[mode.name for mode in WriteParamMode],
                        choices_help=get_all_modes_help(),
                    ),
                    CommandArgs(
                        key="--artifact-name", help="Artifact name from operator to the workflow", required=False
                    ),
                    CommandArgs(
                        key="--artifact-path", help="Artifact path from operator to the workflow", required=False
                    ),
                    CommandArgs(
                        key="--artifact-description",
                        help="Artifact description from operator to the workflow",
                        required=False,
                    ),
                ],
            )
        case CommandName.SET_LIMIT:
            return Command(
                command=CommandName.SET_LIMIT,
                help="Set a workflow limit",
                args=[
                    _session_id_arg(),
                    CommandArgs(
                        key="--limit",
                        type=int,
                        help="Set a workflow limit",
                    ),
                ],
                runner=set_limit,
            )
        case CommandName.SHOW_STATE:
            return Command(
                command=CommandName.SHOW_STATE,
                help="Show a workflow state",
                args=[_session_id_arg()],
                runner=show_state,
            )
        case CommandName.LIST_SESSIONS:
            return Command(
                command=CommandName.LIST_SESSIONS,
                help="List all sessions",
                runner=list_of_sessions,
            )
        case CommandName.HELP_COMPONENTS:
            return Command(
                command=CommandName.HELP_COMPONENTS,
                help="Show components",
                runner=help_components,
            )
        case CommandName.HELP_COMPONENT:
            return Command(
                command=CommandName.HELP_COMPONENT,
                help="Show component description",
                runner=help_component,
                args=[
                    CommandArgs(
                        key="--component-type",
                        help="Type of the component",
                        choices=sorted(COMPONENT_TYPE_BY_KEY),
                    ),
                    CommandArgs(
                        key="--component-name",
                        help="Name of the component",
                    ),
                ],
            )
        case _:
            raise ValueError(f"Unknown command: {command_name}")


def _get_parser() -> CustomArgumentParser:
    parser = CustomArgumentParser(
        description="Workflow Engine CLI",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    shared_parser = argparse.ArgumentParser(add_help=False)
    shared_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    shared_parser.add_argument(
        "--config",
        type=str,
        help=(
            "Path to the workflow engine configuration file "
            "(default: <cwd>/.workflow-engine/workflow_engine_config.json)"
        ),
    )
    shared_parser.add_argument(
        "--work-dir",
        type=str,
        help="Override the runtime work directory (default: <cwd>/.workflow-engine/)",
    )
    shared_parser.add_argument(
        "--storage-dir",
        type=str,
        help="Override the storage directory (default: <runtime-root>/json-storage/)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Workflow engine commands")
    for command_name in CommandName:
        _get_commend(command_name).add_to_parser(subparsers, shared_parser)

    return parser


def main(argv=None):
    """Main entry point for the workflow engine CLI."""
    parser = _get_parser()
    args = parser.parse_args(argv)
    command = _get_commend(CommandName(args.command))
    response = command.run_command(args)
    if args.json:
        print(render_json(response))
    else:
        print(render_text(response))

    sys.exit(get_exit_code(command.command, response.command_status, response.workflow_status).value)
