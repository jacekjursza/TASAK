"""Shared argument parser for MCP and MCP-remote applications."""

import argparse
import sys
import os
import shutil
import textwrap
from typing import Any, Dict, List, Tuple


def _get_binary_name() -> str:
    """Resolve the best display name for the current CLI binary.

    Precedence:
    1) TASAK_BIN_NAME (set by wrappers like `tasak admin create_command`)
    2) sys.argv[0] basename, if not a generic Python launcher
    3) TASAK_CONFIG_NAME (basename without extension), as a helpful hint
    4) Fallback to 'tasak'
    """
    # 1) Explicit override
    env_bin = os.environ.get("TASAK_BIN_NAME")
    if env_bin:
        return env_bin

    # 2) argv[0] if it's not a generic Python entrypoint
    argv0 = os.path.basename(sys.argv[0] or "")
    if argv0 and argv0 not in {"python", "python3", "py", "pytest", "-m"}:
        return argv0

    # 3) Derive from TASAK_CONFIG_NAME if present (strip extension)
    cfg = os.environ.get("TASAK_CONFIG_NAME", "").strip()
    if cfg:
        base = os.path.basename(cfg)
        if base.lower().endswith((".yaml", ".yml")):
            base = base.rsplit(".", 1)[0]
        if base:
            return base

    # 4) Fallback
    return "tasak"


def build_mcp_parser(
    app_name: str, tool_defs: List[Dict[str, Any]], app_type: str = "mcp"
) -> argparse.ArgumentParser:
    """
    Build a unified argument parser for MCP applications.

    Args:
        app_name: Name of the application
        tool_defs: List of tool definitions with schemas
        app_type: Type of app ("mcp" or "mcp-remote")

    Returns:
        Configured ArgumentParser instance
    """
    description = f"Interface for '{app_name}' {app_type.upper()} app."
    parser = argparse.ArgumentParser(prog=f"tasak {app_name}", description=description)

    # Add common flags
    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear local tool definition cache."
    )

    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Start interactive session with the MCP server.",
    )

    # Add subparsers for each tool
    subparsers = parser.add_subparsers(
        dest="tool_name",
        title="Available Tools",
        metavar="",  # Empty string to hide the metavar completely
    )

    for tool in tool_defs:
        tool_name = tool["name"]
        tool_desc = tool.get("description", "")
        tool_parser = subparsers.add_parser(
            tool_name, help=tool_desc, description=tool_desc
        )

        # Add parameters based on tool schema
        schema = tool.get("input_schema", {})
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for prop_name, prop_details in properties.items():
            arg_name = f"--{prop_name}"
            arg_help = prop_details.get("description", "")
            prop_type = prop_details.get("type", "string")
            is_required = prop_name in required

            # Add type information to help text
            if prop_type != "string":
                arg_help = f"{arg_help} (type: {prop_type})"

            # Set appropriate type converter
            type_converter = None
            if prop_type == "integer":
                type_converter = int
            elif prop_type == "number":
                type_converter = float
            elif prop_type == "boolean":
                tool_parser.add_argument(arg_name, action="store_true", help=arg_help)
                continue  # Skip the normal add_argument for boolean

            tool_parser.add_argument(
                arg_name, help=arg_help, required=is_required, type=type_converter
            )

    return parser


def parse_mcp_args(
    app_name: str,
    tool_defs: List[Dict[str, Any]],
    app_args: List[str],
    app_type: str = "mcp",
    mode: str = "dynamic",
) -> Tuple[str, Dict[str, Any], argparse.Namespace]:
    """
    Parse arguments for MCP applications with proper validation.

    Args:
        app_name: Name of the application
        tool_defs: List of tool definitions
        app_args: Raw command line arguments
        app_type: Type of app ("mcp" or "mcp-remote")
        mode: Parsing mode ("dynamic", "curated", or "proxy")

    Returns:
        Tuple of (tool_name, tool_arguments, parsed_namespace)
    """

    # Proxy mode - simple parsing without validation
    if mode == "proxy":
        if not app_args:
            print(f"Usage: tasak {app_name} <tool_name> [args...]", file=sys.stderr)
            sys.exit(1)

        tool_name = app_args[0]
        tool_args = {}

        # Simple argument parsing for proxy mode
        i = 1
        while i < len(app_args):
            arg = app_args[i]
            if arg.startswith("--"):
                key = arg[2:]
                if i + 1 < len(app_args) and not app_args[i + 1].startswith("--"):
                    tool_args[key] = app_args[i + 1]
                    i += 2
                else:
                    tool_args[key] = True
                    i += 1
            else:
                i += 1

        # Return minimal namespace for proxy mode
        namespace = argparse.Namespace(tool_name=tool_name)
        return tool_name, tool_args, namespace

    # If we have no tool definitions, fall back to a permissive proxy-style parse.
    # This tolerates servers that are slow to list tools or when listing fails.
    if not tool_defs:
        # Proxy-like behavior: first positional is tool name; parse --key value pairs
        if not app_args:
            # Nothing to do; return minimal namespace
            return None, {}, argparse.Namespace(tool_name=None)

        # If asking for help, we don't know tools; return minimal to let caller print generic help
        if len(app_args) == 1 and app_args[0] in ("--help", "-h"):
            return None, {}, argparse.Namespace(tool_name=None)

        # Otherwise parse flexibly
        if not app_args[0].startswith("-"):
            tool_name = app_args[0]
            tool_args: Dict[str, Any] = {}
            i = 1
            while i < len(app_args):
                arg = app_args[i]
                if arg.startswith("--"):
                    key = arg[2:]
                    if i + 1 < len(app_args) and not app_args[i + 1].startswith("--"):
                        tool_args[key] = app_args[i + 1]
                        i += 2
                    else:
                        tool_args[key] = True
                        i += 1
                else:
                    i += 1
            return tool_name, tool_args, argparse.Namespace(tool_name=tool_name)

    # Build parser for dynamic/curated modes when tools are known
    parser = build_mcp_parser(app_name, tool_defs, app_type)

    # Parse arguments
    try:
        parsed_args = parser.parse_args(app_args)
    except SystemExit:
        # Only show available tools if no args provided (not for --help)
        if not app_args and tool_defs:
            print(f"\nAvailable tools for {app_name}:")
            for tool in tool_defs:
                print(f"  {tool['name']}: {tool.get('description', 'No description')}")
            binary = _get_binary_name()
            print(
                f"\nUse '{binary} {app_name} <tool_name> --help' for tool-specific help"
            )
        raise

    # Handle special flags that don't require a tool
    if (
        parsed_args.clear_cache
        or getattr(parsed_args, "auth", False)
        or parsed_args.interactive
    ):
        return None, {}, parsed_args

    # Check if tool was specified
    if not hasattr(parsed_args, "tool_name") or not parsed_args.tool_name:
        parser.print_help()
        sys.exit(1)

    tool_name = parsed_args.tool_name

    # Extract tool arguments, filtering out special flags
    SPECIAL_FLAGS = {"tool_name", "clear_cache", "auth", "interactive"}
    tool_args = {
        k: v
        for k, v in vars(parsed_args).items()
        if k not in SPECIAL_FLAGS and v is not None
    }

    # Convert types based on schema (for args that weren't already converted)
    tool_schema = next((t for t in tool_defs if t["name"] == tool_name), None)
    if tool_schema and app_type == "mcp-remote":
        # MCP-remote might need additional type conversion
        for arg_name, arg_value in tool_args.items():
            if arg_value is None:
                continue
            param_schema = (
                tool_schema.get("input_schema", {}).get("properties", {}).get(arg_name)
            )
            if param_schema and not isinstance(arg_value, bool):
                param_type = param_schema.get("type")
                try:
                    if param_type == "integer" and not isinstance(arg_value, int):
                        tool_args[arg_name] = int(arg_value)
                    elif param_type == "number" and not isinstance(arg_value, float):
                        tool_args[arg_name] = float(arg_value)
                    elif param_type == "boolean" and not isinstance(arg_value, bool):
                        tool_args[arg_name] = bool(arg_value)
                except (ValueError, TypeError):
                    print(
                        f"Warning: Could not convert argument '{arg_name}' to type '{param_type}'",
                        file=sys.stderr,
                    )

    return tool_name, tool_args, parsed_args


def show_tool_help(
    app_name: str, tool_defs: List[Dict[str, Any]], app_type: str = "mcp"
):
    """
    Display help information for an MCP application.

    Args:
        app_name: Name of the application
        tool_defs: List of tool definitions
        app_type: Type of app ("mcp" or "mcp-remote")
    """
    print(f"\n{app_name} ({app_type.upper()} Application)")
    print("=" * 50)

    if not tool_defs:
        print("No tools available.")
        print("\nThis could mean:")
        print("  - Authentication is required")
        print("  - The server is not available")
        print("  - There's a configuration issue")
        if app_type == "mcp-remote":
            print(f"\nTry: {_get_binary_name()} admin auth {app_name}")
        return

    print(f"\nAvailable tools ({len(tool_defs)} total):\n")

    for tool in tool_defs:
        tool_name = tool["name"]
        tool_desc = tool.get("description", "No description available")

        # Show tool name and description
        print(f"  {tool_name}")
        print(f"    {tool_desc}")

        # Show parameters
        schema = tool.get("input_schema", {})
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        if properties:
            print("    Parameters:")
            for param_name, param_details in properties.items():
                param_desc = param_details.get("description", "")
                param_type = param_details.get("type", "string")
                is_required = param_name in required

                req_marker = " (required)" if is_required else ""
                type_info = f" [{param_type}]" if param_type != "string" else ""

                print(f"      --{param_name}{type_info}{req_marker}")
                if param_desc:
                    print(f"        {param_desc}")

        print()  # Empty line between tools

    print("Usage examples:")
    # Determine binary/program name dynamically with sensible fallback
    binary = _get_binary_name()
    if tool_defs:
        first_tool = tool_defs[0]["name"]
        print(f"  {binary} {app_name} {first_tool} --help")

        # Show example with parameters if available
        schema = tool_defs[0].get("input_schema", {})
        properties = schema.get("properties", {})
        if properties:
            param_example = list(properties.keys())[0]
            print(f"  {binary} {app_name} {first_tool} --{param_example} <value>")

    print("\nOther commands:")
    print(f"  {binary} {app_name} --interactive  # Interactive mode")
    print(f"  {binary} {app_name} --clear-cache  # Clear cached schemas")
    if app_type == "mcp-remote":
        print(f"  {binary} admin auth {app_name}     # Authenticate with server")


def show_simplified_app_help(
    app_name: str, tool_defs: List[Dict[str, Any]], app_type: str = "mcp"
):
    """
    Print a simplified, agent-friendly help for an MCP application.

    Groups tools into:
    - commands: tools with no required parameters (can run immediately)
    - sub-apps: tools with required parameters (need --help to read more)
    """
    commands: List[Dict[str, Any]] = []
    subapps: List[Dict[str, Any]] = []

    for tool in tool_defs or []:
        schema = tool.get("input_schema", {}) or {}
        required = schema.get("required", []) or []
        (commands if len(required) == 0 else subapps).append(tool)

    # Determine terminal width for nice wrapping
    term_width = shutil.get_terminal_size((100, 20)).columns
    max_width = max(60, min(120, term_width))

    def _print_wrapped_entry(name: str, desc: str):
        header = f"{name} - "
        wrapped = textwrap.fill(
            desc.strip(),
            width=max_width,
            initial_indent=header,
            subsequent_indent=" " * len(header),
            replace_whitespace=True,
        )
        print(wrapped)

    # Commands section
    print(f'"{app_name}" commands:')
    for t in commands:
        name = t.get("name", "")
        desc = t.get("description", "").strip()
        _print_wrapped_entry(name, desc)

    # Sub-apps section (names only, comma-separated)
    print('\n"{}" sub-apps:'.format(app_name))
    if subapps:
        names = ", ".join(t.get("name", "") for t in subapps if t.get("name"))
        wrapped_names = textwrap.fill(
            names,
            width=max_width,
            initial_indent="  ",
            subsequent_indent="  ",
            replace_whitespace=True,
        )
        print(wrapped_names)
    else:
        print("  (none)")

    # Usage hints (consistent with docs app style)
    binary = _get_binary_name()
    # Immediate run hints for commands
    if commands:
        print(
            f"\nRun: {binary} {app_name} <command>            # Runs immediately (no params)"
        )
    # Details for sub-apps
    if subapps:
        print(f"Use: {binary} {app_name} <sub-app> --help   # Details and parameters")
