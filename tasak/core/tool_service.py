import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncio
from .connection_manager import ConnectionManager
from .config import (
    CACHE_TTL as DEFAULT_CACHE_TTL,
    LIST_TIMEOUT,
    CALL_TIMEOUT,
    TOOL_RETRIES,
)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


AUTH_FILE_PATH = Path.home() / ".tasak" / "auth.json"


class ToolService:
    """Facade providing list/call operations over a ConnectionManager.

    This centralizes caching, retries and error mapping so that both the
    daemon and direct CLI share consistent behavior.
    """

    def __init__(self, conn_mgr: Optional[ConnectionManager] = None) -> None:
        self.conn_mgr = conn_mgr or ConnectionManager()

    # ----- Config resolution helpers -----
    def _resolve_mcp_config(
        self, app_name: str, app_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Inline dynamic config (used by mcp-remote wrapper)
        if "_mcp_config" in app_config:
            mcp_config = dict(app_config["_mcp_config"])  # shallow copy
            requires_auth = False
        else:
            # Load from JSON file for classic MCP apps
            cfg_path = app_config.get("config")
            mcp_config = {}
            if cfg_path:
                from os.path import expanduser

                expanded = os.path.expandvars(expanduser(cfg_path))
                try:
                    with open(expanded, "r") as f:
                        raw = f.read()
                    mcp_config = json.loads(os.path.expandvars(raw))
                except Exception:
                    # Fallback defaults
                    mcp_config = {
                        "transport": "sse",
                        "url": "http://localhost:8080/sse",
                    }
            else:
                # Reasonable defaults
                mcp_config = {"transport": "sse", "url": "http://localhost:8080/sse"}
            requires_auth = app_config.get("requires_auth", True)

        # Attach auth header for SSE if required
        if mcp_config.get("transport") == "sse" and requires_auth:
            token = self._get_access_token(app_name)
            headers = dict(mcp_config.get("headers", {}))
            if token:
                headers["Authorization"] = f"Bearer {token}"
            mcp_config["headers"] = headers
        return mcp_config

    def _get_access_token(self, app_name: str) -> Optional[str]:
        if not AUTH_FILE_PATH.exists():
            return None
        try:
            with open(AUTH_FILE_PATH, "r") as f:
                all_tokens = json.load(f)
            token_data = all_tokens.get(app_name)
            if not token_data:
                return None
            return token_data.get("access_token")
        except Exception:
            return None

    # ----- Public API -----
    async def list_tools_async(
        self, app_name: str, app_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        mcp_config = self._resolve_mcp_config(app_name, app_config)
        return await self.list_tools_with_config_async(app_name, mcp_config)

    async def list_tools_with_config_async(
        self, app_name: str, mcp_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        conn = await self.conn_mgr.get(app_name, mcp_config)
        # Cache check
        if (
            conn.tools_cache
            and (time.time() - conn.tools_cached_at) < DEFAULT_CACHE_TTL
        ):
            conn.list_count += 1
            conn.list_cache_hits += 1
            return conn.tools_cache
        # Fetch
        list_timeout = float(mcp_config.get("list_timeout", LIST_TIMEOUT))
        try:
            response = await asyncio.wait_for(
                conn.session.list_tools(), timeout=list_timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Listing tools timed out after {list_timeout:.1f}s")
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            for t in response.tools
        ]
        conn.tools_cache = tools
        conn.tools_cached_at = time.time()
        conn.list_count += 1
        return tools

    async def call_tool_async(
        self,
        app_name: str,
        app_config: Dict[str, Any],
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        mcp_config = self._resolve_mcp_config(app_name, app_config)
        return await self.call_tool_with_config_async(
            app_name, mcp_config, tool_name, arguments
        )

    async def call_tool_with_config_async(
        self,
        app_name: str,
        mcp_config: Dict[str, Any],
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        retries = int(mcp_config.get("retries", TOOL_RETRIES))
        attempts = max(1, retries + 1)
        last_err: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                conn = await self.conn_mgr.get(app_name, mcp_config)
                call_timeout = float(mcp_config.get("call_timeout", CALL_TIMEOUT))
                try:
                    result = await asyncio.wait_for(
                        conn.session.call_tool(tool_name, arguments),
                        timeout=call_timeout,
                    )
                except asyncio.TimeoutError:
                    last_err = TimeoutError(
                        f"Tool '{tool_name}' call timed out after {call_timeout:.1f}s"
                    )
                    raise last_err
                # Extract content similar to daemon
                if getattr(result, "content", None):
                    if len(result.content) > 0:
                        content = result.content[0]
                        if hasattr(content, "text"):
                            conn.call_count += 1
                            return content.text
                        if hasattr(content, "data"):
                            conn.call_count += 1
                            return content.data
                conn.call_count += 1
                return (
                    result
                    if result is not None
                    else {
                        "status": "success",
                        "content": f"Tool {tool_name} executed",
                    }
                )
            except Exception as e:  # noqa: BLE001
                last_err = e
                # Close and retry once
                try:
                    await self.conn_mgr._close(app_name)  # internal close is fine here
                except Exception:
                    pass
                if attempt < attempts:
                    await asyncio.sleep(0.3)
                    continue
                break
        # Raise last error if any
        if last_err:
            raise last_err
        raise RuntimeError("Unknown error during tool call")
