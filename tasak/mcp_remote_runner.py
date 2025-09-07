"""Runner for MCP Remote servers using npx mcp-remote proxy."""

import sys
from typing import Any, Dict, List
from .schema_manager import SchemaManager


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
    if "--clear-cache" in app_args:
        _clear_cache(app_name)
        return

    if "--interactive" in app_args or "-i" in app_args:
        print(f"Starting interactive mode for {app_name}...")
        _run_interactive_mode(server_url)
        return

    # Create a dynamic MCP config that uses mcp-remote as stdio proxy
    # This makes the remote server appear as a local stdio server
    # Note: mcp-remote outputs debug logs that we can't easily suppress
    dynamic_mcp_config = {
        "transport": "stdio",
        "command": ["npx", "-y", "mcp-remote", server_url],
        "env": {
            "NODE_ENV": "production",  # Try to reduce logging
            "DEBUG": "false",  # May help with some debug output
        },
    }

    # Create a modified app_config for MCPRealClient
    # We keep the original config but add our dynamic MCP config
    modified_config = app_config.copy()
    modified_config["_mcp_config"] = dynamic_mcp_config

    # Use MCPRealClient with our dynamic stdio configuration
    # This treats mcp-remote as a local stdio server
    from .mcp_client import run_mcp_app

    # Delegate to the standard MCP handler with our modified config
    # This gives us all the benefits of the unified MCP handling
    # (caching, argument parsing, help generation, etc.)
    run_mcp_app(app_name, modified_config, app_args)


def _clear_cache(app_name: str):
    """Clear cached schema for the app."""
    schema_manager = SchemaManager()
    if schema_manager.delete_schema(app_name):
        print(f"Schema cache cleared for '{app_name}'", file=sys.stderr)
    else:
        print(f"No cached schema found for '{app_name}'", file=sys.stderr)


def _run_interactive_mode(server_url: str):
    """
    Runs interactive mode for an MCP remote server.
    """
    from .mcp_interactive import MCPInteractiveClient

    client = MCPInteractiveClient(server_url)
    client.start()
    client.interactive_loop()
