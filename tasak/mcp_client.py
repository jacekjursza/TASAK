import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import requests


# --- Mock MCP SDK ---
# This is a stand-in for the real mcp-sdk. It allows for development and testing
# without needing the actual SDK or a running server.
class MockSseSession:
    def __init__(self, headers: Dict[str, str]):
        self.headers = headers
        print(
            f"--- Mocking mcp.sse_client.connect() with headers: {self.headers} ---",
            file=sys.stderr,
        )

    def list_tools(self) -> List[Dict[str, Any]]:
        print("--- Mocking mcp.sse_client.list_tools() ---", file=sys.stderr)
        # Only check authorization if header is present (for backward compatibility)
        if "Authorization" in self.headers and not self.headers[
            "Authorization"
        ].startswith("Bearer"):
            raise Exception("Authorization header is invalid.")
        return [
            {
                "name": "create_ticket",
                "description": "Creates a new ticket in the project.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "The project key (e.g., 'PROJ').",
                        },
                        "summary": {
                            "type": "string",
                            "description": "The one-line summary for the ticket.",
                        },
                    },
                    "required": ["project", "summary"],
                },
            },
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        print(
            f"--- Mocking mcp.sse_client.call_tool({tool_name}, ...) ---",
            file=sys.stderr,
        )
        return {"status": "success", "content": f"Successfully called {tool_name}"}


def sse_connect(url: str, headers: Dict[str, str]):
    return MockSseSession(headers)


# --- End Mock MCP SDK ---

CACHE_EXPIRATION_SECONDS = 15 * 60  # 15 minutes
AUTH_FILE_PATH = Path.home() / ".tasak" / "auth.json"
ATLASSIAN_TOKEN_URL = "https://mcp.atlassian.com/oauth2/token"
ATLASSIAN_CLIENT_ID = "5Dzgchq9CCu2EIgv"


def run_mcp_app(app_name: str, app_config: Dict[str, Any], app_args: List[str]):
    """Main entry point for running an MCP application."""
    if "--clear-cache" in app_args:
        _clear_cache(app_name)
        return

    mcp_config = _load_mcp_config(app_config.get("config"))

    # Check if authentication is required (default to True for backward compatibility)
    requires_auth = app_config.get("requires_auth", True)

    if requires_auth:
        access_token = _get_access_token(app_name)
        mcp_config["headers"]["Authorization"] = f"Bearer {access_token}"

    tool_defs = _get_tool_definitions(app_name, mcp_config)
    parser = _build_parser(app_name, tool_defs)
    parsed_args = parser.parse_args(app_args)

    if not hasattr(parsed_args, "tool_name") or not parsed_args.tool_name:
        parser.print_help()
        sys.exit(1)

    tool_name = parsed_args.tool_name
    tool_args = {k: v for k, v in vars(parsed_args).items() if k != "tool_name"}

    session = sse_connect(
        url=mcp_config.get("url"), headers=mcp_config.get("headers", {})
    )
    result = session.call_tool(tool_name, tool_args)

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


# ... (The rest of the functions: _build_parser, _load_mcp_config, etc. remain largely the same) ...


def _clear_cache(app_name: str):
    cache_path = _get_cache_path(app_name)
    if cache_path.exists():
        cache_path.unlink()
        print(f"Cache for '{app_name}' cleared.", file=sys.stderr)
    else:
        print(f"No cache found for '{app_name}'.", file=sys.stderr)


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
    headers = mcp_config.get("headers", {})
    if not url:
        print("Error: 'url' not specified in MCP config.", file=sys.stderr)
        sys.exit(1)
    try:
        session = sse_connect(url=url, headers=headers)
        tool_defs = session.list_tools()
        with open(cache_path, "w") as f:
            json.dump(tool_defs, f, indent=2)
        print(f"Successfully cached tool definitions to {cache_path}", file=sys.stderr)
        return tool_defs
    except Exception as e:
        print(f"Error connecting to MCP server or fetching tools: {e}", file=sys.stderr)
        sys.exit(1)
