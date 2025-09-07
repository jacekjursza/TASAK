"""
Process Pool for MCP Remote - Manages persistent MCP remote proxy processes.

Keeps processes alive for reuse across commands to avoid OAuth re-authentication
and startup overhead.
"""

import asyncio
import logging
import threading
import time
import os
import sys
import atexit as _atexit_mod
from concurrent.futures import Future as _CFuture
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, TextIO

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters

logger = logging.getLogger(__name__)


@dataclass
class PooledProcess:
    """Represents a pooled MCP remote process."""

    process: asyncio.subprocess.Process
    session: ClientSession
    created_at: float
    last_used: float
    app_name: str
    server_url: str
    stdio_context: Any = None  # Store the stdio_client context manager
    # Optional sink for child process stderr; closed on termination
    errlog_handle: Optional[TextIO] = None

    @property
    def is_alive(self) -> bool:
        """Check if process is still running."""
        # If process is None (managed by stdio_client), assume it's alive
        # The session will fail if it's actually dead
        if self.process is None:
            return True
        return self.process.returncode is None

    @property
    def idle_time(self) -> float:
        """Get time since last use in seconds."""
        return time.time() - self.last_used


class MCPRemotePool:
    """
    Manages a pool of MCP remote proxy processes.
    Keeps processes alive for reuse across commands.

    This is a singleton class - only one instance exists per application.
    """

    # Class-level singleton
    _instance = None
    _lock = threading.Lock()

    # Configuration
    IDLE_TIMEOUT = 300  # 5 minutes
    MAX_POOL_SIZE = 10  # Maximum concurrent processes
    CLEANUP_INTERVAL = 30  # Check for idle processes every 30 seconds

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the pool (only once)."""
        if self._initialized:
            return

        self._pool: Dict[str, PooledProcess] = {}
        self._pool_lock = asyncio.Lock()
        self._cleanup_task = None
        self._shutdown = False
        self._initialized = True

        # Dedicated asyncio loop thread to own all stdio contexts
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)

        async def _periodic():
            while not self._shutdown:
                try:
                    await asyncio.sleep(self.CLEANUP_INTERVAL)
                    await self._cleanup_idle_processes()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")

        self._cleanup_task = self._loop.create_task(_periodic())
        self._loop.run_forever()

    def _submit(self, coro: asyncio.coroutines) -> _CFuture:
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    async def _cleanup_idle_processes(self):
        """Remove processes that have been idle for too long."""
        async with self._pool_lock:
            to_remove = []

            for app_name, process in self._pool.items():
                if process.idle_time > self.IDLE_TIMEOUT:
                    logger.info(
                        f"Removing idle process for {app_name} (idle: {process.idle_time:.1f}s)"
                    )
                    to_remove.append(app_name)
                elif not process.is_alive:
                    logger.warning(f"Removing dead process for {app_name}")
                    to_remove.append(app_name)

            for app_name in to_remove:
                await self._terminate_process(app_name)

    async def get_session(self, app_name: str, server_url: str) -> ClientSession:
        """
        Get or create a session for the given app.
        Reuses existing process if available.
        """
        # Ensure creation happens on the dedicated loop
        fut = self._submit(self._get_or_create_session(app_name, server_url))
        return await asyncio.wrap_future(fut)

    async def _get_or_create_session(
        self, app_name: str, server_url: str
    ) -> ClientSession:
        async with self._pool_lock:
            if app_name in self._pool:
                process = self._pool[app_name]
                if process.is_alive and process.server_url == server_url:
                    process.last_used = time.time()
                    logger.debug(f"Reusing existing process for {app_name}")
                    return process.session
                logger.info(f"Removing stale process for {app_name}")
                await self._terminate_process(app_name)
            logger.info(f"Creating new process for {app_name}")
            return await self._create_process(app_name, server_url)

    async def _create_process(self, app_name: str, server_url: str) -> ClientSession:
        """Create a new MCP remote process and session."""
        # Check pool size
        if len(self._pool) >= self.MAX_POOL_SIZE:
            # Remove oldest idle process
            oldest = min(self._pool.values(), key=lambda p: p.last_used)
            logger.info(f"Pool full, removing oldest process: {oldest.app_name}")
            await self._terminate_process(oldest.app_name)

        # Start mcp-remote proxy process using stdio_client
        from mcp.client.stdio import stdio_client

        server_params = StdioServerParameters(
            command="npx", args=["-y", "mcp-remote", server_url], env=None
        )

        # Silence noisy mcp-remote stderr unless in TASAK_DEBUG/TASAK_VERBOSE
        verbose = (os.environ.get("TASAK_DEBUG") == "1") or (
            os.environ.get("TASAK_VERBOSE") == "1"
        )
        err_sink: TextIO
        if verbose:
            err_sink = sys.stderr
        else:
            # Use a devnull sink to discard stderr without leaking fds indefinitely
            err_sink = open(os.devnull, "w")

        # Create and store the context manager
        stdio_ctx = stdio_client(server_params, errlog=err_sink)
        read, write = await stdio_ctx.__aenter__()

        # Create MCP session with proper streams and start background receive loop
        session = ClientSession(read, write)
        # Enter session context to spawn background tasks required for request/response
        await session.__aenter__()
        # Initialize the session
        await session.initialize()

        # Store in pool with context
        pooled = PooledProcess(
            process=None,  # stdio_client manages the process
            session=session,
            created_at=time.time(),
            last_used=time.time(),
            app_name=app_name,
            server_url=server_url,
            stdio_context=stdio_ctx,  # Keep the context alive
            errlog_handle=None if verbose else err_sink,
        )

        self._pool[app_name] = pooled
        logger.info(
            f"Created new process for {app_name} (pool size: {len(self._pool)})"
        )

        return session

    # New: safe helpers that execute on the dedicated loop
    async def list_tools(self, app_name: str, server_url: str) -> List[Dict[str, Any]]:
        async def _inner() -> List[Dict[str, Any]]:
            session = await self._get_or_create_session(app_name, server_url)
            resp = await session.list_tools()
            tools: List[Dict[str, Any]] = []
            for tool in resp.tools:
                tools.append(
                    {
                        "name": getattr(tool, "name", None),
                        "description": getattr(tool, "description", None),
                        "input_schema": getattr(tool, "inputSchema", None),
                    }
                )
            return tools

        fut = self._submit(_inner())
        return await asyncio.wrap_future(fut)

    async def call_tool(
        self, app_name: str, server_url: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        async def _inner():
            session = await self._get_or_create_session(app_name, server_url)
            result = await session.call_tool(tool_name, arguments)
            if getattr(result, "content", None) and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, "text"):
                    return content.text
                if hasattr(content, "data"):
                    return content.data
            return result

        fut = self._submit(_inner())
        return await asyncio.wrap_future(fut)

    async def _terminate_process(self, app_name: str):
        """Terminate a pooled process."""
        if app_name not in self._pool:
            return

        process_info = self._pool[app_name]

        try:
            # Close session context if possible
            if hasattr(process_info.session, "__aexit__"):
                await process_info.session.__aexit__(None, None, None)
            elif hasattr(process_info.session, "close"):
                await process_info.session.close()
        except Exception as e:
            logger.debug(f"Error closing session for {app_name}: {e}")

        # Close stdio context if we have one
        if process_info.stdio_context is not None:
            try:
                await process_info.stdio_context.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"Error closing stdio context for {app_name}: {e}")

        # Close errlog sink if we opened one
        if process_info.errlog_handle is not None:
            try:
                process_info.errlog_handle.close()
            except Exception:
                pass

        # Terminate process if we have one
        elif process_info.process is not None and process_info.is_alive:
            process_info.process.terminate()
            try:
                # Give it time to shutdown gracefully
                await asyncio.wait_for(process_info.process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                # Force kill if it doesn't terminate
                logger.warning(f"Force killing process for {app_name}")
                process_info.process.kill()
                await process_info.process.wait()

        # Remove from pool
        del self._pool[app_name]
        logger.debug(f"Terminated process for {app_name}")

    async def shutdown(self):
        """Shutdown all pooled processes."""
        logger.info("Shutting down process pool")
        self._shutdown = True

        async def _shutdown_inner():
            async with self._pool_lock:
                for app_name in list(self._pool.keys()):
                    await self._terminate_process(app_name)
            # Stop loop after cleanup
            self._loop.call_soon_threadsafe(self._loop.stop)

        fut = self._submit(_shutdown_inner())
        await asyncio.wrap_future(fut)
        logger.info("Process pool shutdown complete")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics for debugging."""
        stats = {
            "pool_size": len(self._pool),
            "max_size": self.MAX_POOL_SIZE,
            "idle_timeout": self.IDLE_TIMEOUT,
            "processes": {},
        }

        for app_name, process in self._pool.items():
            stats["processes"][app_name] = {
                "alive": process.is_alive,
                "idle_time": process.idle_time,
                "created_at": process.created_at,
                "server_url": process.server_url,
            }

        return stats


# Best-effort global cleanup to avoid hanging processes/threads at interpreter exit
def _atexit_shutdown():
    try:
        # Only act if an instance exists
        inst = MCPRemotePool._instance
        if inst is None:
            return
        if getattr(inst, "_shutdown", False):
            return

        # Submit shutdown onto the pool's own loop and wait briefly
        import concurrent.futures as _f

        try:
            fut: _f.Future = inst._submit(inst.shutdown())  # type: ignore[arg-type]
            fut.result(timeout=2.0)
        except Exception:
            # As a last resort, stop the loop and join the thread briefly
            try:
                inst._loop.call_soon_threadsafe(inst._loop.stop)
            except Exception:
                pass
            try:
                inst._thread.join(timeout=0.5)
            except Exception:
                pass
    except Exception:
        # Never block interpreter shutdown due to cleanup issues
        pass


_atexit_mod.register(_atexit_shutdown)
