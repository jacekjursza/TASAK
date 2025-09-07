"""Runner for MCP Remote servers using npx mcp-remote proxy.

This module exposes a stable interface used by tests:
- run_mcp_remote_app
- _print_help
- _run_auth_flow
- _run_interactive_mode
- _clear_cache
"""

import sys
import json
import subprocess
from typing import Any, Dict, List
from .schema_manager import SchemaManager

# Expose MCPRemoteClient at module scope to support test patching
from .mcp_remote_client import MCPRemoteClient


def run_mcp_remote_app(app_name: str, app_config: Dict[str, Any], app_args: List[str]):
    """
    Runs an MCP application through the mcp-remote proxy.

    This dynamically creates a stdio configuration that uses npx mcp-remote
    as a proxy, then delegates to MCPRealClient for all operations.

    The mcp-remote tool handles:
    - OAuth authentication flow
    - Token management
    - SSE connection to remote MCP servers

    Args:
        app_name: Name of the application
        app_config: Configuration dictionary
        app_args: Additional arguments to pass
    """

    # Get the MCP server URL from config
    meta = app_config.get("meta", {})
    server_url = meta.get("server_url")

    if not server_url:
        print(
            f"Error: 'server_url' not specified for mcp-remote app '{app_name}'",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check for special commands that don't need the client
    if "--help" in app_args or "-h" in app_args:
        _print_help(app_name, app_config)
        return

    if "--auth" in app_args:
        print(f"Starting authentication flow for {app_name}...", file=sys.stdout)
        _run_auth_flow(server_url)
        return

    if "--clear-cache" in app_args:
        _clear_cache(app_name)
        return

    if "--interactive" in app_args or "-i" in app_args:
        print(f"Starting interactive mode for {app_name}...")
        _run_interactive_mode(server_url)
        return

    # Mode: curated or dynamic (default dynamic)
    meta = app_config.get("meta", {})
    mode = meta.get("mode", "dynamic")

    schema_manager = SchemaManager()
    tool_defs = None

    if mode == "curated":
        # Try cached schema first
        schema_data = schema_manager.load_schema(app_name)
        if schema_data:
            tool_defs = schema_manager.convert_to_tool_list(schema_data)
            age_days = schema_manager.get_schema_age_days(app_name)
            if age_days and age_days > 7:
                print(
                    f"Schema is {age_days} days old. Consider 'tasak admin refresh {app_name}'.",
                    file=sys.stderr,
                )

    if not tool_defs:
        # Dynamic fetch via MCPRemoteClient (module-level symbol for test patching)
        print("Fetching tool definitions for mcp-remote app...", file=sys.stderr)
        try:
            client = MCPRemoteClient(app_name, app_config)
            tool_defs = client.get_tool_definitions()
        except Exception:
            tool_defs = None

        # Cache in curated/dynamic modes where applicable
        if tool_defs and mode in ("curated", "dynamic"):
            schema_manager.save_schema(app_name, tool_defs)

    # If no tool provided, show available tools
    if not app_args:
        if not tool_defs:
            print("Error: No tools available for '" + app_name + "'.", file=sys.stderr)
            print("Authentication is required for remote servers.", file=sys.stderr)
            print(f"Run: tasak admin auth {app_name}", file=sys.stderr)
            sys.exit(1)
        print(f"Available tools for {app_name}:")
        for t in tool_defs:
            print(f"{t.get('name')}: {t.get('description', '')}")
        return

    # Parse tool invocation
    tool_name = app_args[0]
    args_tokens = app_args[1:]

    # Build argument dict and collect unexpected positionals
    parsed_args: Dict[str, Any] = {}
    unexpected: List[str] = []
    i = 0
    while i < len(args_tokens):
        tok = args_tokens[i]
        if tok.startswith("--"):
            key = tok[2:]
            # Boolean flag if next is another -- or end
            if i + 1 >= len(args_tokens) or args_tokens[i + 1].startswith("--"):
                parsed_args[key] = True
                i += 1
            else:
                parsed_args[key] = args_tokens[i + 1]
                i += 2
        else:
            unexpected.append(tok)
            i += 1

    if unexpected:
        print(
            f"Warning: Ignoring unexpected positional arguments: {unexpected}",
            file=sys.stderr,
        )
        print("Hint: Use --key value format for tool parameters", file=sys.stderr)

    # Execute tool using module-level MCPRemoteClient (allows test patching)
    client = MCPRemoteClient(app_name, app_config)
    try:
        result = client.call_tool(tool_name, parsed_args)
        if isinstance(result, (dict, list)):
            print(json.dumps(result))
        else:
            print(result)
    except Exception as e:
        print(f"Error executing tool: {e}", file=sys.stderr)
        sys.exit(1)


def _clear_cache(app_name: str):
    """Clear cached schema for the app."""
    schema_manager = SchemaManager()
    if schema_manager.delete_schema(app_name):
        print(f"Schema cache cleared for '{app_name}'", file=sys.stderr)
    else:
        print(f"No cached schema found for '{app_name}'", file=sys.stderr)


def _run_auth_flow(server_url: str):
    """Run the OAuth flow via mcp-remote to acquire tokens."""
    try:
        subprocess_result = subprocess.run(
            ["npx", "-y", "mcp-remote", server_url], timeout=120
        )
        # Informational messages
        print(
            "Starting authentication flow — a browser window will open to complete OAuth.",
            file=sys.stderr,
        )
        if subprocess_result.returncode == 0:
            print("Authentication successful via mcp-remote.", file=sys.stderr)
        else:
            print("Authentication may have failed or was cancelled.", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("Authentication timed out.", file=sys.stderr)
    except FileNotFoundError:
        print("Error: npx not found. Please install Node.js and npm.", file=sys.stderr)
    except KeyboardInterrupt:
        print("Authentication cancelled by user.", file=sys.stderr)
    except Exception as e:
        print(f"Error during authentication: {e}", file=sys.stderr)


def _run_interactive_mode(server_url: str):
    """
    Runs interactive mode for an MCP remote server.
    """
    from .mcp_interactive import MCPInteractiveClient

    client = MCPInteractiveClient(server_url)
    client.start()
    client.interactive_loop()


def _print_help(app_name: str, app_config: Dict[str, Any]):
    """Print basic help for mcp-remote app."""
    name = app_config.get("name") or f"MCP Remote app: {app_name}"
    meta = app_config.get("meta", {})
    server_url = meta.get("server_url", "Not configured")

    print(name)
    print("Type: mcp-remote")
    print(f"Server: {server_url}")
    print()
    print(
        f"Usage: tasak {app_name} [--auth|--interactive|-i|--help|-h|<tool> [--key value]…]"
    )
    print("Flags:")
    print("  --auth           Run OAuth authentication (mcp-remote)")
    print("  --interactive,-i Run interactive session")
    print("  --help,-h       Show this help")
    print()
    print("Note: OAuth authentication is required for remote servers.")

    tools = meta.get("tools")
    if tools:
        print("\nAvailable tools:")
        for t in tools:
            print(f"  - {t}")
