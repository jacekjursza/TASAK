"""
Curated App - API Composite Pattern Implementation

Creates unified command-line interfaces that orchestrate multiple underlying systems.
Supports CMD commands, MCP tools, and composite workflows.
"""

import argparse
import json
import re
import subprocess
import sys
from typing import Any, Dict, List
from dataclasses import dataclass

from .mcp_real_client import MCPRealClient
from .mcp_remote_client import MCPRemoteClient
from .config import load_and_merge_configs


@dataclass
class CuratedCommand:
    """Represents a command in a curated app."""

    name: str
    description: str
    backend: Dict[str, Any]
    params: List[Dict[str, Any]] = None
    subcommands: List["CuratedCommand"] = None

    def __post_init__(self):
        if self.params is None:
            self.params = []
        if self.subcommands is None:
            self.subcommands = []


class CuratedApp:
    """
    Orchestrates multiple backends as a composite API.
    Provides a unified interface for complex workflows.
    """

    def __init__(self, app_name: str, config: Dict[str, Any]):
        self.app_name = app_name
        self.config = config
        self.name = config.get("name", app_name)
        self.description = config.get("description", f"Curated app: {app_name}")
        self.commands = self._build_commands(config.get("commands", []))

    def _build_commands(
        self, commands_config: List[Dict[str, Any]]
    ) -> Dict[str, CuratedCommand]:
        """Build command structure from configuration."""
        commands = {}
        for cmd_config in commands_config:
            command = CuratedCommand(
                name=cmd_config["name"],
                description=cmd_config.get("description", ""),
                backend=cmd_config.get("backend", {}),
                params=cmd_config.get("params", []),
                subcommands=[
                    CuratedCommand(
                        name=sub["name"],
                        description=sub.get("description", ""),
                        backend=sub.get("backend", {}),
                        params=sub.get("params", []),
                    )
                    for sub in cmd_config.get("subcommands", [])
                ],
            )
            commands[command.name] = command
        return commands

    def run(self, args: List[str]):
        """Main entry point for running the curated app."""
        if not args:
            self._show_help()
            return

        command_name = args[0]
        command_args = args[1:] if len(args) > 1 else []

        if command_name in ["--help", "-h"]:
            self._show_help()
            return

        if command_name not in self.commands:
            print(f"Error: Unknown command '{command_name}'", file=sys.stderr)
            self._show_help()
            sys.exit(1)

        command = self.commands[command_name]

        # Handle subcommands
        if command.subcommands and command_args:
            subcommand_name = command_args[0]
            for subcommand in command.subcommands:
                if subcommand.name == subcommand_name:
                    self._execute_command(subcommand, command_args[1:])
                    return

            print(
                f"Error: Unknown subcommand '{subcommand_name}' for '{command_name}'",
                file=sys.stderr,
            )
            self._show_command_help(command)
            sys.exit(1)

        # Execute main command
        self._execute_command(command, command_args)

    def _execute_command(self, command: CuratedCommand, args: List[str]):
        """Execute a specific command with its backend."""
        # Parse arguments if params are defined
        context = {}
        if command.params:
            parser = argparse.ArgumentParser(
                prog=f"{self.app_name} {command.name}", description=command.description
            )

            for param in command.params:
                param_copy = param.copy()
                param_name = param_copy.pop("name")

                # Handle special keys
                required = param_copy.pop("required", False)
                help_text = param_copy.pop("help", None)

                if required:
                    parser.add_argument(
                        param_name, help=help_text, required=True, **param_copy
                    )
                else:
                    parser.add_argument(param_name, help=help_text, **param_copy)

            parsed_args = parser.parse_args(args)
            context = vars(parsed_args)

        # Execute backend
        backend_type = command.backend.get("type", "cmd")

        if backend_type == "cmd":
            self._execute_cmd_backend(command.backend, context)
        elif backend_type == "mcp":
            self._execute_mcp_backend(command.backend, context)
        elif backend_type == "composite":
            self._execute_composite_backend(command.backend, context)
        elif backend_type == "conditional":
            self._execute_conditional_backend(command.backend, context)
        else:
            print(f"Error: Unknown backend type '{backend_type}'", file=sys.stderr)
            sys.exit(1)

    def _execute_cmd_backend(self, backend: Dict[str, Any], context: Dict[str, Any]):
        """Execute a shell command backend."""
        command = backend.get("command", [])
        if not command:
            print("Error: No command specified for cmd backend", file=sys.stderr)
            sys.exit(1)

        # Interpolate variables
        interpolated_command = self._interpolate(command, context)

        if isinstance(interpolated_command, str):
            interpolated_command = interpolated_command.split()

        # Execute command
        try:
            if backend.get("async"):
                # Run in background
                subprocess.Popen(interpolated_command)
                print(f"Started: {' '.join(interpolated_command)}")
            else:
                # Run and wait
                result = subprocess.run(
                    interpolated_command,
                    capture_output=backend.get("capture") is not None,
                    text=True,
                )

                if backend.get("required") and result.returncode != 0:
                    print(
                        f"Error: Command failed: {' '.join(interpolated_command)}",
                        file=sys.stderr,
                    )
                    sys.exit(result.returncode)

                if backend.get("capture"):
                    # Store output in context
                    context[backend["capture"]] = result.stdout

        except FileNotFoundError:
            print(
                f"Error: Command not found: {interpolated_command[0]}", file=sys.stderr
            )
            sys.exit(1)
        except Exception as e:
            print(f"Error executing command: {e}", file=sys.stderr)
            sys.exit(1)

    def _execute_mcp_backend(self, backend: Dict[str, Any], context: Dict[str, Any]):
        """Execute an MCP tool backend."""
        app = backend.get("app")
        tool = backend.get("tool")
        args = backend.get("args", {})

        if not app or not tool:
            print("Error: MCP backend requires 'app' and 'tool'", file=sys.stderr)
            sys.exit(1)

        # Interpolate arguments
        interpolated_args = self._interpolate(args, context)

        # Get MCP client for the app
        client = self._get_mcp_client(app)

        if not client:
            print(
                f"Error: MCP app '{app}' not found or not configured", file=sys.stderr
            )
            sys.exit(1)

        try:
            # Call the tool
            result = client.call_tool(tool, interpolated_args)

            # Store result in context if capture is specified
            if backend.get("capture"):
                context[backend["capture"]] = result

            # Print result if not captured
            if not backend.get("capture") and result:
                if isinstance(result, dict):
                    print(json.dumps(result, indent=2))
                else:
                    print(result)

        except Exception as e:
            print(
                f"Error calling MCP tool '{tool}' on app '{app}': {e}", file=sys.stderr
            )
            if backend.get("required"):
                sys.exit(1)

    def _execute_composite_backend(
        self, backend: Dict[str, Any], context: Dict[str, Any]
    ):
        """Execute multiple steps in sequence or parallel."""
        steps = backend.get("steps", [])
        parallel = backend.get("parallel", False)

        if parallel:
            # Run steps in parallel (simplified for now)
            print("Parallel execution not yet implemented")
        else:
            # Run steps sequentially
            for step in steps:
                step_name = step.get("name", "Unnamed step")
                print(f"Executing: {step_name}")

                step_type = step.get("type", "cmd")
                if step_type == "cmd":
                    self._execute_cmd_backend(step, context)
                elif step_type == "mcp":
                    self._execute_mcp_backend(step, context)
                # Nested composite is possible
                elif step_type == "composite":
                    self._execute_composite_backend(step, context)

    def _execute_conditional_backend(
        self, backend: Dict[str, Any], context: Dict[str, Any]
    ):
        """Execute different backends based on conditions."""
        condition = backend.get("condition")
        branches = backend.get("branches", {})

        if not condition:
            print("Error: Conditional backend requires 'condition'", file=sys.stderr)
            sys.exit(1)

        # Evaluate condition (simple variable lookup for now)
        condition_value = self._interpolate(condition, context)

        if condition_value in branches:
            branch_backend = branches[condition_value]
            backend_type = branch_backend.get("type", "cmd")

            if backend_type == "cmd":
                self._execute_cmd_backend(branch_backend, context)
            elif backend_type == "mcp":
                self._execute_mcp_backend(branch_backend, context)
            elif backend_type == "composite":
                self._execute_composite_backend(branch_backend, context)
        else:
            print(
                f"Error: No branch for condition value '{condition_value}'",
                file=sys.stderr,
            )
            sys.exit(1)

    def _get_mcp_client(self, app_name: str):
        """Get or create an MCP client for the specified app."""
        # Load full configuration to find the app
        config = load_and_merge_configs()
        apps_config = config.get("apps_config", {})
        enabled_apps = apps_config.get("enabled_apps", [])

        if app_name not in enabled_apps:
            return None

        app_config = config.get(app_name)
        if not app_config:
            return None

        app_type = app_config.get("type")

        # Create appropriate client based on app type
        if app_type == "mcp":
            return MCPRealClient(app_name, app_config)
        elif app_type == "mcp-remote":
            return MCPRemoteClient(app_name, app_config)
        else:
            return None

    def _interpolate(self, template: Any, context: Dict[str, Any]) -> Any:
        """Replace ${var} with values from context."""
        if isinstance(template, str):
            # Handle ${var:-default} syntax
            pattern = r"\$\{([^}]+)\}"

            def replacer(match):
                expr = match.group(1)
                if ":-" in expr:
                    var, default = expr.split(":-", 1)
                    return str(context.get(var, default))
                return str(context.get(expr, ""))

            return re.sub(pattern, replacer, template)

        elif isinstance(template, dict):
            return {k: self._interpolate(v, context) for k, v in template.items()}

        elif isinstance(template, list):
            return [self._interpolate(item, context) for item in template]

        return template

    def _show_help(self):
        """Show help for the curated app."""
        print(f"\n{self.name}")
        if self.description:
            print(f"{self.description}\n")

        print("Available commands:")
        for cmd_name, cmd in self.commands.items():
            desc = cmd.description or "No description"
            print(f"  {cmd_name:15} {desc}")

            if cmd.subcommands:
                for subcmd in cmd.subcommands:
                    subdesc = subcmd.description or "No description"
                    print(f"    {subcmd.name:13} {subdesc}")

        print(
            f"\nUse '{self.app_name} <command> --help' for more information on a specific command."
        )

    def _show_command_help(self, command: CuratedCommand):
        """Show help for a specific command."""
        print(f"\n{command.name}")
        if command.description:
            print(f"{command.description}\n")

        if command.subcommands:
            print("Subcommands:")
            for subcmd in command.subcommands:
                desc = subcmd.description or "No description"
                print(f"  {subcmd.name:15} {desc}")


def run_curated_app(app_name: str, app_config: Dict[str, Any], app_args: List[str]):
    """Entry point for running a curated app."""
    app = CuratedApp(app_name, app_config)
    app.run(app_args)
