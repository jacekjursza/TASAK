"""
FastAPI server for TASAK daemon.

This server maintains a pool of MCP connections and provides a REST API
for executing tools without the overhead of establishing new connections.
"""

import asyncio
import time
from typing import Any, Dict
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from tasak.core.connection_manager import (
    ConnectionManager,
    DEFAULT_CONN_TTL as CORE_CONN_TTL,
)
from tasak.core.tool_service import ToolService
from tasak.core.config import LOG_LEVEL as CONF_LOG_LEVEL

# Configure logging (level from env; default WARNING)
log_level = getattr(logging, CONF_LOG_LEVEL, logging.WARNING)
logging.basicConfig(
    level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Process start time for uptime
START_TIME = time.time()

# TTLs are managed in core; local cache TTL unused in daemon


class ToolRequest(BaseModel):
    """Request model for tool execution."""

    tool_name: str
    arguments: Dict[str, Any] = {}
    config: Dict[str, Any] = {}


class ToolResponse(BaseModel):
    """Response model for tool execution."""

    success: bool
    result: Any = None
    error: str = None


## Global core manager/service
# Unified core manager/service (used by endpoints below)
CONN_MGR = ConnectionManager()
TOOL_SERVICE = ToolService(CONN_MGR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Start background task for cleanup
    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    # Shutdown
    cleanup_task.cancel()
    await CONN_MGR.close_all()


async def periodic_cleanup():
    """Periodically clean up expired connections."""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            await CONN_MGR.cleanup(CORE_CONN_TTL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


# Create FastAPI app
app = FastAPI(
    title="TASAK Daemon",
    description="Background service for MCP connection pooling",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    try:
        status = getattr(response, "status_code", "?")
    except Exception:
        status = "?"
    logger.debug(
        f"HTTP {request.method} {request.url.path} -> {status} in {duration_ms:.1f}ms"
    )
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    snapshot = CONN_MGR.snapshot()
    return {
        "status": "healthy",
        "connections": len(snapshot),
        "uptime": time.time() - START_TIME,
    }


@app.get("/connections")
async def list_connections():
    """List active connections."""
    snap = CONN_MGR.snapshot()
    return {"connections": [{"app": name, **details} for name, details in snap.items()]}


@app.get("/apps/{app_name}/ping")
async def ping_app(app_name: str, deep: bool = False):
    """Ping an app connection; optionally perform a lightweight server call."""
    start = time.time()
    try:
        # Ensure connection exists; use a minimal config (transport doesn't matter, connection manager may override)
        conn = await CONN_MGR.get(app_name, {"transport": "stdio"})
        details = {
            "app": app_name,
            "has_connection": True,
            "age": time.time() - conn.created_at,
            "idle": time.time() - conn.last_used,
            "cached_tools": len(conn.tools_cache) if conn.tools_cache else 0,
        }
        if deep:
            t0 = time.time()
            try:
                # Perform a quick tools list; may hit cache
                resp = await conn.session.list_tools()
                details["deep_ok"] = True
                details["tools"] = len(resp.tools)
                details["deep_ms"] = (time.time() - t0) * 1000
            except Exception as e:
                details["deep_ok"] = False
                details["error"] = str(e)
        details["elapsed_ms"] = (time.time() - start) * 1000
        return details
    except Exception as e:
        return {"app": app_name, "has_connection": False, "error": str(e)}


@app.get("/metrics")
async def metrics():
    """Return basic daemon metrics."""
    snap = CONN_MGR.snapshot()
    totals = {
        "list_count": sum(v.get("list_count", 0) for v in snap.values()),
        "list_cache_hits": sum(v.get("list_cache_hits", 0) for v in snap.values()),
        "call_count": sum(v.get("call_count", 0) for v in snap.values()),
        "error_count": sum(v.get("error_count", 0) for v in snap.values()),
    }
    return {
        "uptime": time.time() - START_TIME,
        "connections": len(snap),
        **totals,
        "per_app": snap,
    }


@app.post("/tools/list/{app_name}")
async def list_tools(app_name: str, config: Dict[str, Any] = None):
    """List available tools for an app."""
    try:
        logger.debug(f"[tools] list requested app={app_name}")
        tools = await TOOL_SERVICE.list_tools_with_config_async(app_name, config or {})
        return {"tools": tools}

    except Exception as e:
        logger.error(f"[tools] error listing tools for {app_name}: {e}")
        # Metrics are tracked in the core manager; respond with HTTP 500
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/call/{app_name}")
async def call_tool(app_name: str, request: ToolRequest):
    """Execute a tool on an MCP server."""
    attempts = 2  # single retry on failure
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            logger.debug(
                f"[tools] call requested app={app_name} tool={request.tool_name} (try {attempt}/{attempts})"
            )
            result = await TOOL_SERVICE.call_tool_with_config_async(
                app_name,
                request.config or {},
                request.tool_name,
                request.arguments or {},
            )
            return ToolResponse(success=True, result=result)

        except Exception as e:
            last_error = e
            logger.warning(
                f"[tools] call failed app={app_name} tool={request.tool_name} (try {attempt}/{attempts}): {e}"
            )
            # No per-connection metrics here; core tracks within manager

            # On first failure, close connection and retry once
            if attempt < attempts:
                try:
                    await CONN_MGR._close(app_name)  # type: ignore[attr-defined]
                except Exception:
                    pass
                await asyncio.sleep(0.3)
                continue
            else:
                break

    # All attempts failed
    return ToolResponse(
        success=False, error=str(last_error) if last_error else "Unknown error"
    )


@app.post("/shutdown")
async def shutdown():
    """Graceful shutdown endpoint."""
    logger.info("Shutdown requested")
    await CONN_MGR.close_all()

    async def _delayed_exit():
        # Give HTTP response a moment to flush, then terminate process
        try:
            await asyncio.sleep(0.2)
        finally:
            import os

            os._exit(0)

    asyncio.create_task(_delayed_exit())
    return {"status": "shutting down"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
