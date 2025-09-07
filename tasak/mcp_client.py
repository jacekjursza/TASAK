import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import requests
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from .mcp_real_client import MCPRealClient
from .mcp_parser import parse_mcp_args, show_tool_help
from .schema_manager import SchemaManager

CACHE_EXPIRATION_SECONDS = 15 * 60  # 15 minutes
AUTH_FILE_PATH = Path.home() / ".tasak" / "auth.json"
ATLASSIAN_TOKEN_URL = "https://mcp.atlassian.com/oauth2/token"
ATLASSIAN_CLIENT_ID = "5Dzgchq9CCu2EIgv"


def run_mcp_app(app_name: str, app_config: Dict[str, Any], app_args: List[str]):
    """Main entry point for running an MCP application."""
    # Check for special commands that don't need tool definitions
    if "--clear-cache" in app_args:
        _clear_cache(app_name, app_config)
        return

    if "--interactive" in app_args or "-i" in app_args:
        # Interactive mode requires special handling with asyncio
        try:
            mcp_config_path = app_config.get("config")
            if not mcp_config_path:
                print(
                    f"Error: 'config' not specified for MCP app '{app_name}'.",
                    file=sys.stderr,
                )
                sys.exit(1)
            mcp_config = _load_mcp_config(mcp_config_path)
            asyncio.run(run_interactive_session_async(app_name, mcp_config))
        except KeyboardInterrupt:
            print("\nInteractive session terminated by user.", file=sys.stderr)
        return

    # Determine mode
    meta = app_config.get("meta", {})
    mode = meta.get("mode", "dynamic")  # Default to dynamic for backward compatibility

    # Get tool definitions (not needed for proxy mode)
    tool_defs = None
    if mode != "proxy":
        schema_manager = SchemaManager()

        if mode == "curated":
            # Try to load from cached schema first
            schema_data = schema_manager.load_schema(app_name)
            if schema_data:
                tool_defs = schema_manager.convert_to_tool_list(schema_data)
                # Show age of schema if old
                age_days = schema_manager.get_schema_age_days(app_name)
                if age_days and age_days > 7:
                    print(
                        f"Note: Schema is {age_days} days old. Consider 'tasak admin refresh {app_name}'.",
                        file=sys.stderr,
                    )

        # If no cached schema or dynamic mode, fetch from server
        if not tool_defs:
            from .daemon.client import get_mcp_client

            client = get_mcp_client(app_name, app_config)
            tool_defs = client.get_tool_definitions()

            # Cache the tools if we fetched them
            if tool_defs and mode == "dynamic":
                schema_manager.save_schema(app_name, tool_defs)

        if not tool_defs and "--help" not in app_args:
            print(f"Error: No tools available for '{app_name}'.", file=sys.stderr)
            if mode == "curated" and schema_manager.schema_exists(app_name):
                print("Schema file exists but couldn't be loaded.", file=sys.stderr)
            else:
                print("This could mean:", file=sys.stderr)
                print("  - The server is not running", file=sys.stderr)
                print("  - The server has no tools exposed", file=sys.stderr)
                print("  - There's a configuration issue", file=sys.stderr)
                if mode == "curated":
                    print(
                        f"  - No cached schema. Run 'tasak admin refresh {app_name}' first.",
                        file=sys.stderr,
                    )
            sys.exit(1)

    # Parse arguments using the unified parser
    tool_name, tool_args, parsed_args = parse_mcp_args(
        app_name, tool_defs or [], app_args, app_type="mcp", mode=mode
    )

    # Handle help display
    if "--help" in app_args and not tool_name:
        show_tool_help(app_name, tool_defs or [], app_type="mcp")
        return

    # If no tool specified, exit (parse_mcp_args already showed help)
    if not tool_name:
        return

    # Get appropriate client (daemon or direct)
    from .daemon.client import get_mcp_client

    client = get_mcp_client(app_name, app_config)

    try:
        result = client.call_tool(tool_name, tool_args)

        if isinstance(result, dict) or isinstance(result, list):
            print(json.dumps(result, indent=2))
        else:
            print(result)
    except Exception as e:
        # This should rarely happen as MCPRealClient handles most errors
        print(f"Error executing tool: {e}", file=sys.stderr)
        sys.exit(1)


async def run_interactive_session_async(app_name: str, mcp_config: Dict[str, Any]):
    """Runs a persistent, asynchronous interactive session with an MCP app."""
    command = mcp_config.get("command")
    if not command:
        print("Error: 'command' not specified in MCP config.", file=sys.stderr)
        return

    env = mcp_config.get("env", {})
    full_env = os.environ.copy()
    full_env.update(env)

    server_params = StdioServerParameters(
        command=command[0],
        args=command[1:] if len(command) > 1 else [],
        env=full_env,
    )

    is_tty = sys.stdin.isatty()
    if is_tty:
        print(
            f"Starting interactive session with '{app_name}'. Type 'exit' or Ctrl+D to end."
        )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Get tool definitions
                response = await session.list_tools()
                tool_defs = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                    }
                    for tool in response.tools
                ]

                if not tool_defs:
                    print(
                        f"Warning: No tools reported by '{app_name}'.", file=sys.stderr
                    )

                # Main interactive loop
                loop = asyncio.get_running_loop()
                while True:
                    if is_tty:
                        prompt = f"{app_name}> "
                        print(prompt, end="", flush=True)

                    try:
                        line = await loop.run_in_executor(None, sys.stdin.readline)
                    except asyncio.CancelledError:
                        break  # Loop cancelled from outside

                    if not line:  # EOF (Ctrl+D)
                        break

                    line = line.strip()
                    if not line:
                        continue
                    if line.lower() == "exit":
                        break

                    # Parse command and arguments
                    parts = line.split()
                    tool_name = parts[0]
                    tool_args_list = parts[1:]

                    tool_schema = next(
                        (t for t in tool_defs if t["name"] == tool_name), None
                    )
                    if not tool_schema:
                        print(f"Error: Unknown tool '{tool_name}'", file=sys.stderr)
                        continue

                    # Use argparse to parse tool arguments
                    parser = argparse.ArgumentParser(prog=tool_name, add_help=False)
                    input_schema = tool_schema.get("input_schema", {})
                    for prop_name, prop_details in input_schema.get(
                        "properties", {}
                    ).items():
                        parser.add_argument(f"--{prop_name}")

                    try:
                        parsed_args, _ = parser.parse_known_args(tool_args_list)
                        tool_args = {
                            k: v for k, v in vars(parsed_args).items() if v is not None
                        }

                        # Call the tool
                        result = await session.call_tool(tool_name, tool_args)

                        # Display the result
                        if isinstance(result.content, list):
                            for item in result.content:
                                if item.type == "text":
                                    print(item.text)
                                else:
                                    print(json.dumps(item, indent=2))
                        else:
                            print(json.dumps(result.content, indent=2))

                    except Exception as e:
                        print(f"Error calling tool '{tool_name}': {e}", file=sys.stderr)

    except (ConnectionError, TimeoutError, OSError) as e:
        print(f"Error connecting to MCP server: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

    if is_tty:
        print("\nExiting interactive session.")


def _get_access_token(app_name: str) -> str:
    """Gets a valid access token, refreshing if necessary."""
    if not AUTH_FILE_PATH.exists():
        print(
            f"Error: Not authenticated for '{app_name}'. Please run 'tasak auth {app_name}' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(AUTH_FILE_PATH, "r") as f:
        all_tokens = json.load(f)

    token_data = all_tokens.get(app_name)
    if not token_data:
        print(
            f"Error: No authentication data found for '{app_name}'. Please run 'tasak auth {app_name}' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check for expiration (with a 60-second buffer)
    if time.time() > token_data.get("expires_at", 0) - 60:
        print("Access token expired. Refreshing...", file=sys.stderr)
        return _refresh_token(app_name, token_data["refresh_token"])

    return token_data["access_token"]


def _refresh_token(app_name: str, refresh_token: str) -> str:
    """Uses a refresh token to get a new access token."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": ATLASSIAN_CLIENT_ID,
        "refresh_token": refresh_token,
    }
    response = requests.post(ATLASSIAN_TOKEN_URL, data=payload)

    if response.status_code == 200:
        new_token_data = response.json()
        # Atlassian refresh tokens might be single-use, so we save the new one
        if "refresh_token" not in new_token_data:
            new_token_data["refresh_token"] = refresh_token

        from tasak.auth import _save_token  # Avoid circular import

        _save_token(app_name, new_token_data)
        print("Token refreshed successfully.", file=sys.stderr)
        return new_token_data["access_token"]
    else:
        print(
            f"Error refreshing token. Please re-authenticate with 'tasak auth {app_name}'.",
            file=sys.stderr,
        )
        sys.exit(1)


def _clear_cache(app_name: str, app_config: Dict[str, Any]):
    # Use the real client to clear cache
    client = MCPRealClient(app_name, app_config)
    client.clear_cache()


def _load_mcp_config(path_str: str) -> Dict[str, Any]:
    expanded_path = Path(os.path.expandvars(os.path.expanduser(path_str)))
    if not expanded_path.exists():
        print(f"Error: MCP config file not found at {expanded_path}", file=sys.stderr)
        sys.exit(1)
    raw_content = expanded_path.read_text()
    substituted_content = os.path.expandvars(raw_content)
    try:
        return json.loads(substituted_content)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {expanded_path}: {e}", file=sys.stderr)
        sys.exit(1)


def _get_tool_definitions(
    app_name: str,
    config_path: Path,
    cache_path: Path = None,
    always_fetch: bool = False,
) -> List[Dict[str, Any]]:
    """Fetches or loads cached tool definitions for an MCP app."""
    if cache_path and cache_path.exists() and not always_fetch:
        try:
            with open(cache_path, "r") as f:
                cache_data = json.load(f)
                if (
                    time.time() - cache_data.get("timestamp", 0)
                    < CACHE_EXPIRATION_SECONDS
                ):
                    return cache_data["tools"]
        except (json.JSONDecodeError, KeyError):
            pass

    return []
