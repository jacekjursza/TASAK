import argparse
import subprocess
import sys
from typing import Any, Dict, List


def run_cmd_app(app_config: Dict[str, Any], app_args: List[str]):
    """Runs a 'cmd' type application."""
    meta = app_config.get("meta", {})
    mode = meta.get("mode", "proxy")

    if mode == "proxy":
        _run_proxy_mode(meta, app_args)
    elif mode == "curated":
        _run_curated_mode(meta, app_args)
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)


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


def _run_curated_mode(meta: Dict[str, Any], app_args: List[str]):
    """Executes the command in curated mode."""
    base_command = meta.get("command")
    params_config = meta.get("params", [])

    if not base_command:
        print("'command' not specified for curated mode.", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description=meta.get("description", "Curated command")
    )
    for param in params_config:
        param_name = param.pop("name")
        parser.add_argument(param_name, **param)

    parsed_args = parser.parse_args(app_args)

    if isinstance(base_command, str):
        command_list = base_command.split()
    else:
        command_list = list(base_command)

    for arg_name, arg_value in vars(parsed_args).items():
        if arg_value is not None:
            for p_config in params_config:
                if p_config["dest"] == arg_name:
                    maps_to = p_config.get("maps_to")
                    if maps_to:
                        command_list.append(maps_to)
                        if not isinstance(arg_value, bool) or arg_value:
                            command_list.append(str(arg_value))
                    # if no maps_to, it's a positional argument
                    else:
                        command_list.append(str(arg_value))
                    break

    _execute_command(command_list)


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
