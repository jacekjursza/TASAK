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
from .schema_manager import SchemaManager

CACHE_EXPIRATION_SECONDS = 15 * 60  # 15 minutes
AUTH_FILE_PATH = Path.home() / ".tasak" / "auth.json"
ATLASSIAN_TOKEN_URL = "https://mcp.atlassian.com/oauth2/token"
ATLASSIAN_CLIENT_ID = "5Dzgchq9CCu2EIgv"


def run_mcp_app(app_name: str, app_config: Dict[str, Any], app_args: List[str]):
    """Main entry point for running an MCP application."""
    if "--interactive" in app_args:
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

    if "--clear-cache" in app_args:
        _clear_cache(app_name, app_config)
        return

    # Determine mode
    meta = app_config.get("meta", {})
    mode = meta.get("mode", "dynamic")  # Default to dynamic for backward compatibility

    if mode == "proxy":
        # Proxy mode - pass arguments directly without validation
        _run_proxy_mode(app_name, app_config, app_args)
        return

    # Get tool definitions (for curated and dynamic modes)
    tool_defs = None
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
        client = MCPRealClient(app_name, app_config)
        tool_defs = client.get_tool_definitions()

    if not tool_defs:
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

    parser = _build_parser(app_name, tool_defs)
    parsed_args = parser.parse_args(app_args)

    if not hasattr(parsed_args, "tool_name") or not parsed_args.tool_name:
        parser.print_help()
        sys.exit(1)

    tool_name = parsed_args.tool_name
    # Filter out TASAK-specific arguments before passing to MCP server
    TASAK_FLAGS = {"clear_cache"}  # Add more as needed
    tool_args = {
        k: v
        for k, v in vars(parsed_args).items()
        if k != "tool_name" and k not in TASAK_FLAGS
    }

    # Get the tool schema and convert argument types
    tool_schema = next((t for t in tool_defs if t["name"] == tool_name), None)
    if tool_schema:
        for arg_name, arg_value in tool_args.items():
            if arg_value is None:
                continue
            param_schema = (
                tool_schema.get("input_schema", {}).get("properties", {}).get(arg_name)
            )
            if param_schema:
                param_type = param_schema.get("type")
                try:
                    if param_type == "integer":
                        tool_args[arg_name] = int(arg_value)
                    elif param_type == "number":
                        tool_args[arg_name] = float(arg_value)
                    elif param_type == "boolean":
                        tool_args[arg_name] = bool(arg_value)
                except (ValueError, TypeError):
                    print(
                        f"Warning: Could not convert argument '{arg_name}' to type '{param_type}'",
                        file=sys.stderr,
                    )

    # Call the tool using real MCP client
    client = MCPRealClient(app_name, app_config)
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

                        # Print result
                        if result.content and len(result.content) > 0:
                            content = result.content[0]
                            if hasattr(content, "text"):
                                print(content.text)
                            elif hasattr(content, "data"):
                                print(json.dumps(content.data, indent=2))
                        else:
                            print(f"Tool '{tool_name}' executed.")

                    except Exception as e:
                        print(f"Error calling tool '{tool_name}': {e}", file=sys.stderr)

    except (ConnectionError, TimeoutError, OSError) as e:
        print(f"Error connecting to MCP server: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

    if is_tty:
        print("\nExiting interactive session.")


def _run_proxy_mode(app_name: str, app_config: Dict[str, Any], app_args: List[str]):
    """Run MCP app in proxy mode - no validation, direct pass-through."""
    if not app_args:
        print(f"Usage: tasak {app_name} <tool_name> [args...]", file=sys.stderr)
        sys.exit(1)

    tool_name = app_args[0]
    tool_args = {}

    # Simple argument parsing - everything after tool name
    i = 1
    while i < len(app_args):
        arg = app_args[i]
        if arg.startswith("--"):
            key = arg[2:]
            if i + 1 < len(app_args) and not app_args[i + 1].startswith("--"):
                # Has value
                tool_args[key] = app_args[i + 1]
                i += 2
            else:
                # Boolean flag
                tool_args[key] = True
                i += 1
        else:
            i += 1

    # Call tool without validation
    client = MCPRealClient(app_name, app_config)
    result = client.call_tool(tool_name, tool_args)

    if isinstance(result, dict) or isinstance(result, list):
        print(json.dumps(result, indent=2))
    else:
        print(result)


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


def _build_parser(
    app_name: str, tool_defs: List[Dict[str, Any]]
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"tasak {app_name}", description=f"Interface for '{app_name}' MCP app."
    )
    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear local tool definition cache."
    )
    subparsers = parser.add_subparsers(dest="tool_name", title="Available Tools")
    for tool in tool_defs:
        tool_name = tool["name"]
        tool_desc = tool.get("description", "")
        tool_parser = subparsers.add_parser(
            tool_name, help=tool_desc, description=tool_desc
        )
        schema = tool.get("input_schema", {})
        for prop_name, prop_details in schema.get("properties", {}).items():
            arg_name = f"--{prop_name}"
            arg_help = prop_details.get("description", "")
            is_required = prop_name in schema.get("required", [])
            tool_parser.add_argument(arg_name, help=arg_help, required=is_required)
    return parser


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
    app_name: str, mcp_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    cache_path = _get_cache_path(app_name)
    if _is_cache_valid(cache_path):
        print("Loading tool definitions from cache.", file=sys.stderr)
        with open(cache_path, "r") as f:
            return json.load(f)
    return _fetch_and_cache_definitions(app_name, mcp_config, cache_path)


def _get_cache_path(app_name: str) -> Path:
    cache_dir = Path.home() / ".tasak" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{app_name}.json"


def _is_cache_valid(cache_path: Path) -> bool:
    if not cache_path.exists():
        return False
    age = time.time() - cache_path.stat().st_mtime
    return age < CACHE_EXPIRATION_SECONDS


def _fetch_and_cache_definitions(
    app_name: str, mcp_config: Dict[str, Any], cache_path: Path
) -> List[Dict[str, Any]]:
    print(f"Fetching tool definitions for '{app_name}' from server...", file=sys.stderr)
    transport = mcp_config.get("transport")
    if transport != "sse":
        print(
            f"Error: Unsupported MCP transport '{transport}'. MVP only supports 'sse'.",
            file=sys.stderr,
        )
        sys.exit(1)
    url = mcp_config.get("url")
    if not url:
        print("Error: 'url' not specified in MCP config.", file=sys.stderr)
        sys.exit(1)
    # This function is deprecated - now handled by MCPRealClient
    print(
        "Warning: Using deprecated function _fetch_and_cache_definitions",
        file=sys.stderr,
    )
    return []
