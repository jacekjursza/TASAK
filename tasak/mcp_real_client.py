"""Real MCP client implementation using official MCP SDK."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters
import logging

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

CACHE_EXPIRATION_SECONDS = 15 * 60  # 15 minutes
AUTH_FILE_PATH = Path.home() / ".tasak" / "auth.json"


class MCPRealClient:
    """Synchronous wrapper around async MCP client."""

    def __init__(self, app_name: str, app_config: Dict[str, Any]):
        self.app_name = app_name
        self.app_config = app_config
        self.mcp_config = self._load_mcp_config(app_config.get("config"))
        self.cache_path = self._get_cache_path(app_name)
        self.requires_auth = app_config.get("requires_auth", True)

    def _load_mcp_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load MCP configuration from file."""
        if not config_file:
            return {
                "transport": "sse",
                "url": "http://localhost:8080/sse",
                "headers": {},
            }

        config_path = Path(config_file)
        if not config_path.exists():
            print(f"Warning: Config file {config_file} not found", file=sys.stderr)
            return {
                "transport": "sse",
                "url": "http://localhost:8080/sse",
                "headers": {},
            }

        with open(config_path, "r") as f:
            return json.load(f)

    def _get_cache_path(self, app_name: str) -> Path:
        """Get cache path for tool definitions."""
        cache_dir = Path.home() / ".tasak" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{app_name}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache is still valid."""
        if not cache_path.exists():
            return False

        cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return cache_age < timedelta(seconds=CACHE_EXPIRATION_SECONDS)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions from server or cache."""
        # Check cache first
        if self._is_cache_valid(self.cache_path):
            print("Loading tool definitions from cache.", file=sys.stderr)
            with open(self.cache_path, "r") as f:
                return json.load(f)

        # Fetch from server
        print(
            f"Fetching tool definitions for '{self.app_name}' from server...",
            file=sys.stderr,
        )

        # Add auth header if required
        headers = self.mcp_config.get("headers", {}).copy()
        if self.requires_auth:
            access_token = self._get_access_token()
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

        # Run async function in sync context
        tools = asyncio.run(self._fetch_tools_async(headers))

        # Cache the results
        if tools:
            with open(self.cache_path, "w") as f:
                json.dump(tools, f, indent=2)
            print(
                f"Successfully cached tool definitions to {self.cache_path}",
                file=sys.stderr,
            )

        return tools

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        headers = self.mcp_config.get("headers", {}).copy()
        if self.requires_auth:
            access_token = self._get_access_token()
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

        # Run async function in sync context
        result = asyncio.run(self._call_tool_async(tool_name, arguments, headers))
        return result

    def _get_access_token(self) -> Optional[str]:
        """Get access token if authentication is required."""
        if not self.requires_auth:
            return None

        if not AUTH_FILE_PATH.exists():
            print(
                f"Error: Not authenticated for '{self.app_name}'. Please run 'tasak auth {self.app_name}' first.",
                file=sys.stderr,
            )
            sys.exit(1)

        with open(AUTH_FILE_PATH, "r") as f:
            all_tokens = json.load(f)

        token_data = all_tokens.get(self.app_name)
        if not token_data:
            print(
                f"Error: No authentication data found for '{self.app_name}'. Please run 'tasak auth {self.app_name}' first.",
                file=sys.stderr,
            )
            sys.exit(1)

        # For now, just return the access token
        # TODO: Add token refresh logic if needed
        return token_data.get("access_token")

    async def _fetch_tools_async(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Async function to fetch tools from MCP server."""
        transport = self.mcp_config.get("transport", "sse")

        try:
            if transport == "sse":
                # SSE transport (for GOK and remote servers)
                url = self.mcp_config.get("url", "http://localhost:8080/sse")

                async with sse_client(url, headers=headers) as (read, write):
                    async with ClientSession(read, write) as session:
                        # Initialize the session
                        await session.initialize()

                        # List available tools
                        response = await session.list_tools()

                        # Convert to our format
                        tools = []
                        for tool in response.tools:
                            tools.append(
                                {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "input_schema": tool.inputSchema,
                                }
                            )

                        return tools

            elif transport == "stdio":
                # STDIO transport (for local servers)
                command = self.mcp_config.get("command", ["python", "server.py"])
                env = self.mcp_config.get("env", {})

                # Merge with current environment
                import os

                full_env = os.environ.copy()
                full_env.update(env)

                server_params = StdioServerParameters(
                    command=command[0],
                    args=command[1:] if len(command) > 1 else [],
                    env=full_env,
                )

                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        response = await session.list_tools()

                        tools = []
                        for tool in response.tools:
                            tools.append(
                                {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "input_schema": tool.inputSchema,
                                }
                            )

                        return tools
            else:
                print(f"Unsupported transport: {transport}", file=sys.stderr)
                return []

        except Exception as e:
            print(
                f"Error connecting to MCP server or fetching tools: {e}",
                file=sys.stderr,
            )
            return []

    async def _call_tool_async(
        self, tool_name: str, arguments: Dict[str, Any], headers: Dict[str, str]
    ) -> Any:
        """Async function to call a tool on MCP server."""
        transport = self.mcp_config.get("transport", "sse")

        try:
            if transport == "sse":
                url = self.mcp_config.get("url", "http://localhost:8080/sse")

                async with sse_client(url, headers=headers) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        # Call the tool
                        result = await session.call_tool(tool_name, arguments)

                        # Extract the result
                        if result.content and len(result.content) > 0:
                            content = result.content[0]
                            if hasattr(content, "text"):
                                return content.text
                            elif hasattr(content, "data"):
                                return content.data

                        return {
                            "status": "success",
                            "content": f"Tool {tool_name} executed",
                        }

            elif transport == "stdio":
                command = self.mcp_config.get("command", ["python", "server.py"])
                env = self.mcp_config.get("env", {})

                # Merge with current environment
                import os

                full_env = os.environ.copy()
                full_env.update(env)

                server_params = StdioServerParameters(
                    command=command[0],
                    args=command[1:] if len(command) > 1 else [],
                    env=full_env,
                )

                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        result = await session.call_tool(tool_name, arguments)

                        if result.content and len(result.content) > 0:
                            content = result.content[0]
                            if hasattr(content, "text"):
                                return content.text
                            elif hasattr(content, "data"):
                                return content.data

                        return {
                            "status": "success",
                            "content": f"Tool {tool_name} executed",
                        }
            else:
                return {"error": f"Unsupported transport: {transport}"}

        except Exception as e:
            print(f"Error calling tool: {e}", file=sys.stderr)
            return {"error": str(e)}

    def clear_cache(self):
        """Clear the cache for this app."""
        if self.cache_path.exists():
            self.cache_path.unlink()
            print(f"Cache for '{self.app_name}' cleared.", file=sys.stderr)
        else:
            print(f"No cache found for '{self.app_name}'.", file=sys.stderr)
