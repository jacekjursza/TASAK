"""MCP Remote client that communicates through mcp-remote proxy with process pooling."""

import asyncio
import sys
from typing import Any, Dict, List

import logging

from .mcp_remote_pool import MCPRemotePool

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class MCPRemoteClient:
    """Client for MCP Remote servers using process pool for performance."""

    def __init__(self, app_name: str, app_config: Dict[str, Any]):
        self.app_name = app_name
        self.app_config = app_config
        self.meta = app_config.get("meta", {})
        self.server_url = self.meta.get("server_url")
        self.pool = MCPRemotePool()  # Singleton pool

        if not self.server_url:
            raise ValueError(f"No server_url specified for {app_name}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions through the pooled proxy."""
        # Run async function in sync context
        return asyncio.run(self._fetch_tools_async())

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool through the pooled proxy."""
        # Run async function in sync context
        return asyncio.run(self._call_tool_async(tool_name, arguments))

    async def _fetch_tools_async(self) -> List[Dict[str, Any]]:
        """Async function to fetch tools using pooled connection."""
        try:
            # Get session from pool (reuses if available)
            session = await self.pool.get_session(self.app_name, self.server_url)

            logger.debug(f"Fetching tools for {self.app_name}")

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

            logger.info(f"Fetched {len(tools)} tools for {self.app_name}")
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
        """Async function to call a tool using pooled connection."""
        try:
            # Get session from pool (reuses if available)
            session = await self.pool.get_session(self.app_name, self.server_url)

            logger.debug(f"Calling tool {tool_name} for {self.app_name}")

            # Call the tool
            result = await session.call_tool(tool_name, arguments)

            # Extract the result with proper validation
            if (
                hasattr(result, "content")
                and result.content
                and len(result.content) > 0
            ):
                content = result.content[0]
                if hasattr(content, "text"):
                    return content.text
                elif hasattr(content, "data"):
                    return content.data

            # If result doesn't have expected structure, return it as-is or a default
            if result:
                return result

            return {
                "status": "success",
                "content": f"Tool {tool_name} executed",
            }

        except Exception as e:
            error_msg = str(e)
            print(
                f"Error calling tool through mcp-remote: {error_msg}", file=sys.stderr
            )

            # Check if it's an authentication error
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                print(
                    f"Authentication required. Run: tasak admin auth {self.app_name}",
                    file=sys.stderr,
                )
                sys.exit(1)

            # For other errors, raise them instead of exiting
            raise RuntimeError(f"Failed to call tool {tool_name}: {error_msg}") from e
