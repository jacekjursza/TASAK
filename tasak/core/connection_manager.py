import asyncio
import os
import time
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any, Dict, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from .config import (
    CONN_TTL as _CONF_CONN_TTL,
    INIT_TIMEOUT as _CONF_INIT_TIMEOUT,
    INIT_ATTEMPTS as _CONF_INIT_ATTEMPTS,
)
from .transports.mcp_remote import MCPRemoteSessionAdapter, NoopContext


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


# Use centralized config default for TTL
DEFAULT_CONN_TTL = _CONF_CONN_TTL


@dataclass
class Connection:
    session: ClientSession
    context: AbstractAsyncContextManager
    mcp_config: Dict[str, Any]
    created_at: float
    last_used: float
    tools_cache: Optional[list] = None
    tools_cached_at: float = 0.0
    list_count: int = 0
    list_cache_hits: int = 0
    call_count: int = 0
    error_count: int = 0

    def touch(self) -> None:
        self.last_used = time.time()

    def is_expired(self, ttl: int = DEFAULT_CONN_TTL) -> bool:
        return (time.time() - self.last_used) > ttl


class ConnectionManager:
    """Manages per-app MCP connections with TTL and cleanup.

    This is used by both daemon and direct paths to centralize session
    creation and lifecycle management.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._conns: Dict[str, Connection] = {}

    async def get(self, app_name: str, mcp_config: Dict[str, Any]) -> Connection:
        """Get or create a connection keyed by app_name.

        mcp_config must include either:
        - transport: "stdio" with command/env
        - transport: "sse" with url/headers
        """
        async with self._lock:
            # Reuse if present and not expired
            conn = self._conns.get(app_name)
            if conn and not conn.is_expired():
                conn.touch()
                return conn

            # Close existing if present
            if conn:
                try:
                    await self._close(app_name)
                except Exception:
                    pass

            # Create new
            new_conn = await self._create_connection(app_name, mcp_config)
            self._conns[app_name] = new_conn
            return new_conn

    async def _create_connection(
        self, app_name: str, mcp_config: Dict[str, Any]
    ) -> Connection:
        transport = mcp_config.get("transport", "stdio")
        init_timeout = float(mcp_config.get("init_timeout", _CONF_INIT_TIMEOUT))

        # Allow small retry loop for robustness
        attempts = int(mcp_config.get("init_attempts", _CONF_INIT_ATTEMPTS))
        last_err: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            context = None
            try:
                if transport == "mcp-remote":
                    server_url = mcp_config.get("server_url") or mcp_config.get("url")
                    if not server_url:
                        raise ValueError(
                            "mcp-remote transport requires 'server_url' or 'url'"
                        )
                    session = MCPRemoteSessionAdapter(app_name, server_url)
                    return Connection(
                        session=session,  # type: ignore[arg-type]
                        context=NoopContext(),
                        mcp_config=mcp_config,
                        created_at=time.time(),
                        last_used=time.time(),
                    )
                if transport == "stdio":
                    command = mcp_config.get("command", ["python", "server.py"])
                    env = mcp_config.get("env", {})

                    full_env = os.environ.copy()
                    full_env.update(env or {})

                    params = StdioServerParameters(
                        command=command[0],
                        args=command[1:] if len(command) > 1 else [],
                        env=full_env,
                    )

                    context = stdio_client(params)
                    read, write = await asyncio.wait_for(
                        context.__aenter__(), timeout=init_timeout
                    )
                    session = ClientSession(read, write)
                    await asyncio.wait_for(session.__aenter__(), timeout=init_timeout)
                    await asyncio.wait_for(session.initialize(), timeout=init_timeout)
                    return Connection(
                        session=session,
                        context=context,
                        mcp_config=mcp_config,
                        created_at=time.time(),
                        last_used=time.time(),
                    )

                elif transport == "sse":
                    url = mcp_config.get("url")
                    headers = mcp_config.get("headers", {})
                    context = sse_client(url, headers=headers)
                    read, write = await asyncio.wait_for(
                        context.__aenter__(), timeout=init_timeout
                    )
                    session = ClientSession(read, write)
                    await asyncio.wait_for(session.__aenter__(), timeout=init_timeout)
                    await asyncio.wait_for(session.initialize(), timeout=init_timeout)
                    return Connection(
                        session=session,
                        context=context,
                        mcp_config=mcp_config,
                        created_at=time.time(),
                        last_used=time.time(),
                    )
                else:
                    raise ValueError(f"Unsupported transport: {transport}")

            except Exception as e:  # noqa: BLE001
                last_err = e
                # Best-effort close context before retry
                try:
                    if context is not None:
                        await context.__aexit__(None, None, None)
                except Exception:
                    pass
                # Backoff between attempts
                await asyncio.sleep(0.2 * attempt)
                continue

        raise last_err if last_err else RuntimeError("Failed to create MCP connection")

    async def cleanup(self, ttl: int = DEFAULT_CONN_TTL) -> None:
        async with self._lock:
            expired = [name for name, c in self._conns.items() if c.is_expired(ttl)]
            for name in expired:
                try:
                    await self._close(name)
                except Exception:
                    pass

    async def _close(self, app_name: str) -> None:
        conn = self._conns.get(app_name)
        if not conn:
            return
        try:
            try:
                await conn.session.__aexit__(None, None, None)
            finally:
                await conn.context.__aexit__(None, None, None)
        finally:
            self._conns.pop(app_name, None)

    async def close_all(self) -> None:
        async with self._lock:
            names = list(self._conns.keys())
        for name in names:
            try:
                await self._close(name)
            except Exception:
                pass

    # Introspection helpers (optional)
    def snapshot(self) -> Dict[str, Any]:
        now = time.time()
        return {
            name: {
                "created_at": c.created_at,
                "last_used": c.last_used,
                "age": now - c.created_at,
                "idle": now - c.last_used,
                "list_count": c.list_count,
                "list_cache_hits": c.list_cache_hits,
                "call_count": c.call_count,
                "error_count": c.error_count,
            }
            for name, c in self._conns.items()
        }
