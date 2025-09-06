"""Runner for MCP Remote servers using npx mcp-remote proxy."""

import subprocess
import sys
from typing import Any, Dict, List
from .mcp_remote_client import MCPRemoteClient
from .schema_manager import SchemaManager


def run_mcp_remote_app(app_name: str, app_config: Dict[str, Any], app_args: List[str]):
    """
    Runs an MCP application through the mcp-remote proxy.

    This uses npx to run the official mcp-remote tool which handles:
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

    # Check for special commands
    if "--help" in app_args or "-h" in app_args:
        _print_help(app_name, app_config)
        return

    if "--auth" in app_args:
        print(f"Starting authentication flow for {app_name}...")
        _run_auth_flow(server_url)
        return

    if "--interactive" in app_args or "-i" in app_args:
        print(f"Starting interactive mode for {app_name}...")
        _run_interactive_mode(server_url)
        return

    if "--clear-cache" in app_args:
        _clear_cache(app_name)
        return

    # Use the new MCPRemoteClient for normal tool operations
    client = MCPRemoteClient(app_name, app_config)

    # Determine mode from config
    mode = meta.get("mode", "dynamic")

    # Get tool definitions
    tool_defs = None
    schema_manager = SchemaManager()

    if mode == "curated":
        # Try cached schema first
        schema_data = schema_manager.load_schema(app_name)
        if schema_data:
            tool_defs = schema_manager.convert_to_tool_list(schema_data)
            age_days = schema_manager.get_schema_age_days(app_name)
            if age_days and age_days > 7:
                print(
                    f"Note: Schema is {age_days} days old. Consider 'tasak admin refresh {app_name}'.",
                    file=sys.stderr,
                )

    # If no cached schema or dynamic mode, fetch from server
    if not tool_defs:
        print(
            f"Fetching tool definitions for '{app_name}' via mcp-remote...",
            file=sys.stderr,
        )
        tool_defs = client.get_tool_definitions()

        # Cache the tools if we fetched them
        if tool_defs and mode == "dynamic":
            schema_manager.save_schema(app_name, tool_defs)

    if not tool_defs:
        print(f"Error: No tools available for '{app_name}'.", file=sys.stderr)
        print("This could mean:", file=sys.stderr)
        print("  - Authentication is required", file=sys.stderr)
        print("  - The server is not available", file=sys.stderr)
        print("  - There's a configuration issue", file=sys.stderr)
        print(f"\nTry: tasak admin auth {app_name}", file=sys.stderr)
        sys.exit(1)

    # Parse arguments to find tool and its args
    if not app_args:
        # Show available tools
        print(f"Available tools for {app_name}:")
        for tool in tool_defs:
            print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
        return

    tool_name = app_args[0]
    tool_args = {}
    unexpected_args = []

    # Simple argument parsing
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
            # Collect unexpected positional arguments
            unexpected_args.append(arg)
            i += 1

    # Warn about unexpected positional arguments
    if unexpected_args:
        print(
            f"Warning: Ignoring unexpected positional arguments: {unexpected_args}",
            file=sys.stderr,
        )
        print("Hint: Use --key value format for tool parameters", file=sys.stderr)

    # Call the tool
    import json

    try:
        result = client.call_tool(tool_name, tool_args)
        if isinstance(result, dict) or isinstance(result, list):
            print(json.dumps(result, indent=2))
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
    """
    Runs authentication flow for an MCP remote server.
    """
    # For authentication only, we can add a flag if mcp-remote supports it
    # Otherwise just run normally and it will trigger auth
    cmd = ["npx", "-y", "mcp-remote", server_url]

    print("Starting authentication flow...", file=sys.stderr)
    print("A browser window will open for authentication.", file=sys.stderr)

    try:
        result = subprocess.run(cmd, timeout=120)  # 2 minute timeout for auth
        if result.returncode == 0:
            print("Authentication successful!", file=sys.stderr)
        else:
            print("Authentication may have failed or was cancelled.", file=sys.stderr)

    except subprocess.TimeoutExpired:
        print("Authentication timed out.", file=sys.stderr)
    except FileNotFoundError:
        print("Error: npx not found. Please install Node.js first.", file=sys.stderr)
        print("Visit: https://nodejs.org/", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nAuthentication cancelled by user.", file=sys.stderr)
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
    """
    Prints help information for an mcp-remote app.
    """
    description = app_config.get("name", f"MCP Remote app: {app_name}")
    meta = app_config.get("meta", {})
    server_url = meta.get("server_url", "Not configured")

    print(f"\n{description}")
    print("Type: mcp-remote")
    print(f"Server: {server_url}")
    print("\nUsage:")
    print(f"  tasak {app_name}              # Connect to the MCP server")
    print(f"  tasak {app_name} --auth       # Authenticate with the server")
    print(f"  tasak {app_name} --interactive # Interactive mode (send commands)")
    print(f"  tasak {app_name} --help       # Show this help message")
    print("\nNotes:")
    print("  - Uses npx mcp-remote proxy for connection")
    print("  - Handles OAuth authentication automatically")
    print("  - Requires Node.js to be installed")
    print("\nAuthentication:")
    print("  The first time you connect, a browser will open for OAuth login.")
    print("  Tokens are cached locally by mcp-remote for future use.")

    # Show available tools if configured
    tools = meta.get("tools", [])
    if tools:
        print("\nAvailable tools:")
        for tool in tools:
            print(f"  - {tool}")
