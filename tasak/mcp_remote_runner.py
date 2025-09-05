"""Runner for MCP Remote servers using npx mcp-remote proxy."""

import subprocess
import sys
from typing import Any, Dict, List


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

    # Build the npx command
    cmd = ["npx", "-y", "mcp-remote", server_url]

    # Add any additional arguments from config
    extra_args = meta.get("args", [])
    if extra_args:
        cmd.extend(extra_args)

    # Add user-provided arguments
    if app_args:
        cmd.extend(app_args)

    print(f"Connecting to {app_name} via mcp-remote...", file=sys.stderr)
    print(f"Server: {server_url}", file=sys.stderr)
    print(
        "Note: This will open a browser for authentication if needed.", file=sys.stderr
    )

    try:
        # Run mcp-remote interactively
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)

    except FileNotFoundError:
        print("Error: npx not found. Please install Node.js first.", file=sys.stderr)
        print("Visit: https://nodejs.org/", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nConnection interrupted by user.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error running mcp-remote: {e}", file=sys.stderr)
        sys.exit(1)


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
