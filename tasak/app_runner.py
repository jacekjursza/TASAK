import subprocess
import sys
from typing import Any, Dict, List


def run_cmd_app(app_config: Dict[str, Any], app_args: List[str]):
    """Runs a 'cmd' type application in proxy mode."""
    meta = app_config.get("meta", {})
    # Only proxy mode is supported for cmd apps
    # For complex workflows, use type: curated instead
    _run_proxy_mode(meta, app_args)


def _run_proxy_mode(meta: Dict[str, Any], app_args: List[str]):
    """Executes the command in proxy mode."""
    base_command = meta.get("command")
    if not base_command:
        print(
            "'command' not specified in app configuration for proxy mode.",
            file=sys.stderr,
        )
        sys.exit(1)

    if isinstance(base_command, str):
        command_list = base_command.split()
    else:
        command_list = list(base_command)

    full_command = command_list + app_args
    _execute_command(full_command)


def _execute_command(command: List[str]):
    """Executes a command and streams its output."""
    print(f"Running command: {' '.join(command)}", file=sys.stderr)

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()
        if process.returncode != 0:
            print(f"\nCommand exited with code {process.returncode}", file=sys.stderr)
            sys.exit(process.returncode)

    except FileNotFoundError:
        print(f"Error: Command not found: {command[0]}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
