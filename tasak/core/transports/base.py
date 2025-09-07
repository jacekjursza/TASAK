"""
Base transport interfaces for TASAK core.

Currently the core inlines stdio/SSE setup within ConnectionManager, but
these Protocols define the intended seam for future extractions and tests.
"""

from __future__ import annotations

from typing import Any, Dict, Protocol


class TransportSession(Protocol):
    async def list_tools(self) -> Any: ...  # returns an object with `.tools`
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any: ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...


class TransportAdapter(Protocol):
    async def connect(
        self, app_name: str, config: Dict[str, Any]
    ) -> TransportSession: ...
    async def close(self) -> None: ...
