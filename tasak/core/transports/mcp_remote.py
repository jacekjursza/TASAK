"""
MCP Remote transport adapter for the core ConnectionManager.

Bridges the Python core to the Node-based `mcp-remote` proxy using the
existing MCPRemotePool. The adapter exposes a minimal session-like API
with `list_tools()` and `call_tool()` coroutines and a no-op `__aexit__`.
"""

from __future__ import annotations

from typing import Any, Dict, List


class MCPRemoteSessionAdapter:
    """Session-like adapter that marshals calls through MCPRemotePool."""

    def __init__(self, app_name: str, server_url: str):
        from tasak.mcp_remote_pool import MCPRemotePool  # lazy import to avoid cycles

        self.app_name = app_name
        self.server_url = server_url
        self._pool = MCPRemotePool()

    async def list_tools(self) -> Any:
        """Return a response-like object with `.tools` for parity with SDK."""
        tools: List[Dict[str, Any]] = await self._pool.list_tools(
            self.app_name, self.server_url
        )

        class _Resp:
            def __init__(self, tools: List[Dict[str, Any]]):
                self.tools = _Items([_Item(t) for t in tools])

        class _Items(list):
            pass

        class _Item:
            def __init__(self, t: Dict[str, Any]):
                self.name = t.get("name")
                self.description = t.get("description")
                self.inputSchema = t.get("input_schema")

        return _Resp(tools)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        return await self._pool.call_tool(
            self.app_name, self.server_url, tool_name, arguments
        )

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        """On close, terminate the pooled process for this app."""
        # Terminate only this app's process; swallow errors
        try:
            await self._pool._terminate_process(self.app_name)  # type: ignore[attr-defined]
        except Exception:
            pass


class NoopContext:
    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None
