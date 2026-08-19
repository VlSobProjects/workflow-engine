import argparse
import sys
from argparse import Namespace
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from workflow_engine.cli.contract import CommandName, CommandResult, CommandStatus
from workflow_engine.cli.exit_codes import ExitCode, get_exit_code
from workflow_engine.cli.presenters import render_json, render_text
from workflow_engine.cli.use_cases import (
    export_artifact,
    help_component,
    help_components,
    init_session,
    list_of_sessions,
    resume_workflow,
    run_workflow,
    set_input,
    set_limit,
    show_state,
)
from workflow_engine.exceptions import WorkflowEngineError
from workflow_engine.help_contract.models import COMPONENT_TYPE_BY_KEY


class CommandLineError(Exception):
    """A malformed command line.

    argparse reports a bad call by writing to stdout and exiting on the spot, which destroys the
    `--json` contract: a caller that parses stdout gets usage text instead of a document. The parser
    raises this instead, so the entry point decides what to write and where.
    """

    def __init__(self, message: str, usage: str) -> None:
        self.usage = usage
        super().__init__(message)


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CommandLineError(message, self.format_usage())


@dataclass
class CommandArgs:
    key: str
    help: str
    required: bool = field(default=True)
    type: type = field(default=str)
    action: str = field(default="store")
    choices: list[str] | None = field(default=None)
    choices_help: str | None = field(default=None)

    def add_argument(self, command):
        kwargs: dict[str, object] = {"help": self.help, "action": self.action}
        if self.action == "store_true":
            # A boolean flag takes no type or choices; requiredness of a mutually exclusive group
            # member is owned by the group, so it stays optional here.
            if self.required:
                kwargs["required"] = self.required
        else:
            kwargs["type"] = self.type
            kwargs["required"] = self.required
            if self.choices is not None:
                kwargs["choices"] = self.choices
        command.add_argument(self.key, **kwargs)


@dataclass
class Command:
    command: CommandName
    help: str
    runner: Callable[[CommandName, Namespace], CommandResult]
    args: list[CommandArgs] = field(default_factory=list)
    exclusive_args: list[CommandArgs] = field(default_factory=list)
    # A group of alternatives is required by default; `resume` declares one that is not, because an
    # answer is optional there and its absence re-presents the question. See ADR 013.
    exclusive_required: bool = field(default=True)

    def add_to_parser(self, parser: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser):
        command_parser = parser.add_parser(self.command.value, help=self.help, parents=[shared_parser])
        for arg in self.args:
            arg.add_argument(command_parser)
        if self.exclusive_args:
            group = command_parser.add_mutually_exclusive_group(required=self.exclusive_required)
            for arg in self.exclusive_args:
                arg.add_argument(group)

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


def _input_arg(required: bool) -> CommandArgs:
    return CommandArgs(
        key="--input",
        help="Bind an input value: NAME[:TYPE]=VALUE (repeatable). TYPE is a codec name (see help-components)",
        required=required,
        action="append",
    )


def _export_dir_arg() -> CommandArgs:
    return CommandArgs(
        key="--export-dir",
        help="Directory the declared deliverables are exported into on completion (overrides config export_dir)",
        required=False,
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
                    ),
                    _input_arg(required=False),
                    _export_dir_arg(),
                ],
            )
        case CommandName.SET_INPUT:
            return Command(
                command=CommandName.SET_INPUT,
                help="Bind input values to an unstarted session",
                runner=set_input,
                args=[
                    _session_id_arg(),
                    _input_arg(required=True),
                ],
            )
        case CommandName.RESUME:
            return Command(
                command=CommandName.RESUME,
                help="Resume a workflow, optionally answering the question it is paused at",
                runner=resume_workflow,
                args=[
                    _session_id_arg(),
                    _export_dir_arg(),
                ],
                exclusive_args=[
                    CommandArgs(
                        key="--answer",
                        help=(
                            "Answer to the paused interactive node, as a JSON object: 'status' "
                            "(success|failure), 'values', optional 'text', 'error_code', 'message', 'actor'"
                        ),
                        required=False,
                    ),
                    CommandArgs(
                        key="--answer-file",
                        help="Path to a file holding the same JSON answer document",
                        required=False,
                    ),
                ],
                exclusive_required=False,
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
        case CommandName.EXPORT_ARTIFACT:
            return Command(
                command=CommandName.EXPORT_ARTIFACT,
                help="Export one artifact or all declared deliverables of a session to a directory",
                runner=export_artifact,
                args=[
                    _session_id_arg(),
                    CommandArgs(key="--target-dir", help="Directory the artifacts are copied into"),
                ],
                exclusive_args=[
                    CommandArgs(
                        key="--artifact-name",
                        help="Logical name of the single artifact to export",
                        required=False,
                    ),
                    CommandArgs(
                        key="--all",
                        help="Export all declared deliverables of the session",
                        required=False,
                        action="store_true",
                    ),
                ],
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
                        help="Name of the component; when omitted, shows the type description and its components",
                        required=False,
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


def _command_from_argv(argv: Sequence[str]) -> CommandName | None:
    """The command a malformed call meant, when its first positional token names a known one."""
    for token in argv:
        if token.startswith("-"):
            continue
        try:
            return CommandName(token)
        except ValueError:
            return None
    return None


def _report_command_line_error(error: CommandLineError, argv: Sequence[str]) -> None:
    """Report a malformed command line: the operator text on stderr, and a result when `--json`.

    stdout belongs to the answer, so the message and the usage go to stderr unconditionally. A caller
    that asked for JSON gets a `CommandResult` there and never has to parse usage text.
    """
    print(f"Error: {error}", file=sys.stderr)
    print(error.usage, file=sys.stderr, end="")
    if "--json" in argv:
        print(
            render_json(
                CommandResult(
                    command=_command_from_argv(argv),
                    command_status=CommandStatus.ERROR,
                    message=str(error),
                    errors={"command_line": str(error)},
                    data=None,
                )
            )
        )


def main(argv=None):
    """Main entry point for the workflow engine CLI."""
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    parser = _get_parser()
    try:
        args = parser.parse_args(effective_argv)
    except CommandLineError as error:
        _report_command_line_error(error, effective_argv)
        sys.exit(ExitCode.ERROR.value)
    command = _get_commend(CommandName(args.command))
    response = command.run_command(args)
    if args.json:
        print(render_json(response))
    else:
        print(render_text(response))

    sys.exit(get_exit_code(command.command, response.command_status, response.workflow_status).value)
