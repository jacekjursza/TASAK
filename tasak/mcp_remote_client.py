"""MCP Remote client that communicates through mcp-remote proxy."""

import asyncio
import sys
from typing import Any, Dict, List

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import logging

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class MCPRemoteClient:
    """Client for MCP Remote servers that uses mcp-remote proxy."""

    def __init__(self, app_name: str, app_config: Dict[str, Any]):
        self.app_name = app_name
        self.app_config = app_config
        self.meta = app_config.get("meta", {})
        self.server_url = self.meta.get("server_url")
        self.proxy_process = None

        if not self.server_url:
            raise ValueError(f"No server_url specified for {app_name}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions through the proxy."""
        # Run async function in sync context
        return asyncio.run(self._fetch_tools_async())

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool through the proxy."""
        # Run async function in sync context
        return asyncio.run(self._call_tool_async(tool_name, arguments))

    async def _fetch_tools_async(self) -> List[Dict[str, Any]]:
        """Async function to fetch tools through mcp-remote proxy."""
        try:
            # Start mcp-remote proxy process
            proxy_cmd = ["npx", "-y", "mcp-remote", self.server_url]

            logger.debug(f"Starting mcp-remote proxy: {' '.join(proxy_cmd)}")

            # Use StdioServerParameters which expects separate command and args
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "mcp-remote", self.server_url],
                env=None,  # Will use current environment
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()

                    # List available tools
                    tools_result = await session.list_tools()

                    tools = []
                    for tool in tools_result.tools:
                        tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "input_schema": tool.inputSchema,
                            }
                        )

                    return tools

        except Exception as e:
            print(f"Error fetching tools through mcp-remote: {e}", file=sys.stderr)
            # Check if it's an auth issue
            if "401" in str(e) or "unauthorized" in str(e).lower():
                print(
                    f"Authentication required. Run: tasak admin auth {self.app_name}",
                    file=sys.stderr,
                )
            return []

    async def _call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Async function to call a tool through mcp-remote proxy."""
        try:
            # Start mcp-remote proxy process
            server_params = StdioServerParameters(
                command="npx", args=["-y", "mcp-remote", self.server_url], env=None
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
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

        except Exception as e:
            print(f"Error calling tool through mcp-remote: {e}", file=sys.stderr)
            if "401" in str(e) or "unauthorized" in str(e).lower():
                print(
                    f"Authentication required. Run: tasak admin auth {self.app_name}",
                    file=sys.stderr,
                )
                sys.exit(1)
            sys.exit(1)
