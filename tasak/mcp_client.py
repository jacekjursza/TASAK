import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import requests
from .mcp_real_client import MCPRealClient

CACHE_EXPIRATION_SECONDS = 15 * 60  # 15 minutes
AUTH_FILE_PATH = Path.home() / ".tasak" / "auth.json"
ATLASSIAN_TOKEN_URL = "https://mcp.atlassian.com/oauth2/token"
ATLASSIAN_CLIENT_ID = "5Dzgchq9CCu2EIgv"


def run_mcp_app(app_name: str, app_config: Dict[str, Any], app_args: List[str]):
    """Main entry point for running an MCP application."""
    if "--clear-cache" in app_args:
        _clear_cache(app_name, app_config)
        return

    # Use real MCP client
    client = MCPRealClient(app_name, app_config)

    # Get tool definitions
    tool_defs = client.get_tool_definitions()

    if not tool_defs:
        print(f"Error: No tools available for '{app_name}'.", file=sys.stderr)
        print("This could mean:", file=sys.stderr)
        print("  - The server is not running", file=sys.stderr)
        print("  - The server has no tools exposed", file=sys.stderr)
        print("  - There's a configuration issue", file=sys.stderr)
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

    # Call the tool using real MCP client
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


# ... (The rest of the functions: _build_parser, _load_mcp_config, etc. remain largely the same) ...


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
