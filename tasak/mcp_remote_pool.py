"""
Process Pool for MCP Remote - Manages persistent MCP remote proxy processes.

Keeps processes alive for reuse across commands to avoid OAuth re-authentication
and startup overhead.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Any

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

        # Start cleanup task
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background task to clean up idle processes."""

        def cleanup_worker():
            while not self._shutdown:
                time.sleep(self.CLEANUP_INTERVAL)
                try:
                    # Run async cleanup in new event loop
                    asyncio.run(self._cleanup_idle_processes())
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")

        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()

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
        async with self._pool_lock:
            # Check if we have a live process
            if app_name in self._pool:
                process = self._pool[app_name]

                if process.is_alive and process.server_url == server_url:
                    process.last_used = time.time()
                    logger.debug(f"Reusing existing process for {app_name}")
                    return process.session
                else:
                    # Process died or server URL changed, remove it
                    logger.info(f"Removing stale process for {app_name}")
                    await self._terminate_process(app_name)

            # Create new process
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

        # Create and store the context manager
        stdio_ctx = stdio_client(server_params)
        read, write = await stdio_ctx.__aenter__()

        # Create MCP session with proper streams
        session = ClientSession(read, write)

        # Initialize session
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
        )

        self._pool[app_name] = pooled
        logger.info(
            f"Created new process for {app_name} (pool size: {len(self._pool)})"
        )

        return session

    async def _terminate_process(self, app_name: str):
        """Terminate a pooled process."""
        if app_name not in self._pool:
            return

        process_info = self._pool[app_name]

        try:
            # Close session if possible
            if hasattr(process_info.session, "close"):
                await process_info.session.close()
        except Exception as e:
            logger.debug(f"Error closing session for {app_name}: {e}")

        # Close stdio context if we have one
        if process_info.stdio_context is not None:
            try:
                await process_info.stdio_context.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"Error closing stdio context for {app_name}: {e}")

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

        async with self._pool_lock:
            for app_name in list(self._pool.keys()):
                await self._terminate_process(app_name)

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
