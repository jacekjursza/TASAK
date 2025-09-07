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
from typing import Any, Dict, List, Optional
from .schema_manager import SchemaManager
from .mcp_parser import show_tool_help, show_simplified_app_help

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
        # Simplified grouped help with descriptions
        tool_defs = _get_tool_defs_for_help(app_name, app_config)
        show_simplified_app_help(app_name, tool_defs or [], app_type="mcp-remote")
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

    # Always resolve tool definitions for help/validation below (with 1-day TTL)
    tool_defs = _get_tool_defs_for_help(app_name, app_config)

    # If no tool provided, show minimal list of methods only
    if not app_args:
        for t in tool_defs or []:
            name = t.get("name")
            if name:
                print(name)
        return

    # Parse tool invocation
    tool_name = app_args[0]
    args_tokens = app_args[1:]

    # Check if tool exists and if required params are satisfied
    tool_schema = next(
        (t for t in (tool_defs or []) if t.get("name") == tool_name), None
    )
    if tool_schema is None:
        print(f"Error: Unknown tool '{tool_name}'", file=sys.stderr)
        sys.exit(1)
    required = (tool_schema.get("input_schema", {}) or {}).get("required", []) or []
    # Explicit tool help request
    if "--help" in args_tokens or "-h" in args_tokens:
        show_tool_help(app_name, [tool_schema], app_type="mcp-remote")
        return
    if not args_tokens and not required:
        # Immediate call with no params
        client = MCPRemoteClient(app_name, app_config)
        try:
            result = client.call_tool(tool_name, {})
            if isinstance(result, (dict, list)):
                print(json.dumps(result))
            else:
                print(result)
        except Exception as e:
            print(f"Error executing tool: {e}", file=sys.stderr)
            sys.exit(1)
        return

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

    # If required params are still missing after parsing, show focused help
    missing = [r for r in required if r not in parsed_args]
    if missing:
        show_tool_help(app_name, [tool_schema], app_type="mcp-remote")
        return

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


def _get_tool_defs_for_help(
    app_name: str, app_config: Dict[str, Any]
) -> Optional[List[Dict[str, Any]]]:
    """Return tool definitions, refreshing cache if older than 1 day.

    - Prefer cached schema if age < 1 day
    - Otherwise, fetch via MCPRemoteClient quietly; fallback to cache on failure
    """
    schema_manager = SchemaManager()
    schema_data = schema_manager.load_schema(app_name)
    if schema_data:
        age_days = schema_manager.get_schema_age_days(app_name) or 0
        if age_days < 1:
            return schema_manager.convert_to_tool_list(schema_data)

    # Cache is missing or stale (>= 1 day) — fetch quietly
    try:
        client = MCPRemoteClient(app_name, app_config)
        tools = client.get_tool_definitions() or []
        if tools:
            schema_manager.save_schema(app_name, tools)
            return tools
    except Exception:
        pass

    # Fallback to whatever cache exists
    if schema_data:
        return schema_manager.convert_to_tool_list(schema_data)
    return []


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

    # Prefer tools listed in config meta only; detailed list is rendered separately
    tools = meta.get("tools")
    if tools:
        print("\nAvailable tools:")
        for t in tools:
            print(f"  - {t}")
