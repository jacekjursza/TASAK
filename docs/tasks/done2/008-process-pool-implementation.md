# Process Pool Implementation for MCP Remote

## Problem Statement

Every MCP remote command spawns a new `npx mcp-remote` process, causing:
- 3-5 second startup overhead per command
- OAuth re-authentication attempts
- Poor user experience for repeated commands
- Unnecessary resource usage

## Current Implementation

**Location:** `mcp_remote_client.py`
```python
async def _fetch_tools_async(self):
    # Every call creates NEW process
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "mcp-remote", self.server_url]
    )
    async with stdio_client(server_params) as (read, write):
        # Process dies when context exits
```

**Problem:** Each command creates and destroys a process, losing connection state.

## Proposed Solution: Process Pool

### Architecture

```
┌─────────────┐
│   TASAK     │
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│      MCPRemotePool              │
│  ┌──────────────────────────┐   │
│  │ "atlassian" → Process    │   │
│  │  - Created: 10:00:00     │   │
│  │  - Last used: 10:05:23   │   │
│  │  - Status: alive         │   │
│  ├──────────────────────────┤   │
│  │ "github" → Process       │   │
│  │  - Created: 10:02:00     │   │
│  │  - Last used: 10:03:00   │   │
│  │  - Status: idle (kill?)  │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

### Implementation Design

```python
# tasak/mcp_remote_pool.py

import asyncio
import time
import threading
from typing import Dict, Optional, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

@dataclass
class PooledProcess:
    """Represents a pooled MCP remote process."""
    process: asyncio.subprocess.Process
    read_stream: any  # Type from MCP SDK
    write_stream: any  # Type from MCP SDK
    session: ClientSession
    created_at: float
    last_used: float
    app_name: str
    server_url: str

class MCPRemotePool:
    """
    Manages a pool of MCP remote proxy processes.
    Keeps processes alive for reuse across commands.
    """

    # Class-level singleton pool
    _instance = None
    _lock = threading.Lock()

    # Configuration
    IDLE_TIMEOUT = 300  # 5 minutes
    MAX_POOL_SIZE = 10  # Maximum concurrent processes

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
        self._cleanup_task = None
        self._initialized = True

        # Start cleanup task
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background task to clean up idle processes."""
        def cleanup_worker():
            while True:
                time.sleep(30)  # Check every 30 seconds
                self._cleanup_idle_processes()

        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()

    def _cleanup_idle_processes(self):
        """Remove processes idle for too long."""
        now = time.time()
        to_remove = []

        with self._lock:
            for app_name, process in self._pool.items():
                if now - process.last_used > self.IDLE_TIMEOUT:
                    to_remove.append(app_name)

            for app_name in to_remove:
                self._terminate_process(app_name)

    async def get_session(self, app_name: str, server_url: str) -> ClientSession:
        """
        Get or create a session for the given app.
        Reuses existing process if available.
        """
        # Check if we have a live process
        if app_name in self._pool:
            process = self._pool[app_name]
            process.last_used = time.time()

            # Verify process is still alive
            if process.process.returncode is None:
                return process.session
            else:
                # Process died, remove it
                del self._pool[app_name]

        # Create new process
        return await self._create_process(app_name, server_url)

    async def _create_process(self, app_name: str, server_url: str) -> ClientSession:
        """Create a new MCP remote process and session."""
        # Check pool size
        if len(self._pool) >= self.MAX_POOL_SIZE:
            # Remove oldest idle process
            oldest = min(self._pool.values(), key=lambda p: p.last_used)
            self._terminate_process(oldest.app_name)

        # Start mcp-remote process
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "mcp-remote", server_url],
            env=None
        )

        # Create process but DON'T use context manager (we manage lifecycle)
        process = await asyncio.create_subprocess_exec(
            server_params.command,
            *server_params.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=server_params.env
        )

        # Create MCP session
        read_stream = process.stdout
        write_stream = process.stdin
        session = ClientSession(read_stream, write_stream)

        # Initialize session
        await session.initialize()

        # Store in pool
        pooled = PooledProcess(
            process=process,
            read_stream=read_stream,
            write_stream=write_stream,
            session=session,
            created_at=time.time(),
            last_used=time.time(),
            app_name=app_name,
            server_url=server_url
        )

        self._pool[app_name] = pooled
        return session

    def _terminate_process(self, app_name: str):
        """Terminate a pooled process."""
        if app_name not in self._pool:
            return

        process = self._pool[app_name]

        # Close session
        if process.session:
            # Note: MCP SDK might not have explicit close
            pass

        # Terminate process
        if process.process.returncode is None:
            process.process.terminate()
            # Give it time to shutdown gracefully
            try:
                process.process.wait(timeout=2)
            except asyncio.TimeoutError:
                process.process.kill()

        # Remove from pool
        del self._pool[app_name]

    def shutdown(self):
        """Shutdown all pooled processes."""
        for app_name in list(self._pool.keys()):
            self._terminate_process(app_name)
```

### Integration with MCPRemoteClient

```python
# Modified mcp_remote_client.py

class MCPRemoteClient:
    """Client for MCP Remote servers using process pool."""

    def __init__(self, app_name: str, app_config: Dict[str, Any]):
        self.app_name = app_name
        self.app_config = app_config
        self.server_url = app_config.get("meta", {}).get("server_url")
        self.pool = MCPRemotePool()  # Singleton

    async def _fetch_tools_async(self) -> List[Dict[str, Any]]:
        """Fetch tools using pooled connection."""
        try:
            # Get session from pool (reuses if available)
            session = await self.pool.get_session(self.app_name, self.server_url)

            # Use existing session to list tools
            tools_result = await session.list_tools()

            tools = []
            for tool in tools_result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                })

            return tools

        except Exception as e:
            print(f"Error fetching tools: {e}", file=sys.stderr)
            return []

    async def _call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call tool using pooled connection."""
        try:
            # Get session from pool
            session = await self.pool.get_session(self.app_name, self.server_url)

            # Call tool
            result = await session.call_tool(tool_name, arguments)

            # Extract result
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, "text"):
                    return content.text
                elif hasattr(content, "data"):
                    return content.data

            return {"status": "success", "content": f"Tool {tool_name} executed"}

        except Exception as e:
            print(f"Error calling tool: {e}", file=sys.stderr)
            sys.exit(1)
```

### Cleanup and Lifecycle Management

```python
# In main.py or cli entry point

import atexit
import signal

def cleanup_pool():
    """Ensure pool is cleaned up on exit."""
    pool = MCPRemotePool()
    pool.shutdown()

# Register cleanup
atexit.register(cleanup_pool)

# Handle signals
def signal_handler(sig, frame):
    cleanup_pool()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

## Performance Improvements

### Before (Current)
```
Command 1: tasak atlassian list
  - Start npx process: 2s
  - OAuth check: 1s
  - Execute: 0.5s
  Total: 3.5s

Command 2: tasak atlassian create
  - Start npx process: 2s
  - OAuth check: 1s
  - Execute: 0.5s
  Total: 3.5s

Total for 2 commands: 7s
```

### After (With Pool)
```
Command 1: tasak atlassian list
  - Start npx process: 2s (first time)
  - OAuth check: 1s
  - Execute: 0.5s
  Total: 3.5s

Command 2: tasak atlassian create
  - Reuse process: 0s
  - No OAuth: 0s
  - Execute: 0.5s
  Total: 0.5s

Total for 2 commands: 4s (43% faster)
Total for 10 commands: 8s (vs 35s = 77% faster!)
```

## Edge Cases and Considerations

### 1. Process Death Detection
```python
if process.process.returncode is not None:
    # Process died unexpectedly
    del self._pool[app_name]
    # Create new one
```

### 2. Connection Errors
```python
try:
    result = await session.call_tool(...)
except ConnectionError:
    # Connection lost, remove from pool
    self._terminate_process(app_name)
    # Retry with new process
    session = await self._create_process(app_name, server_url)
    result = await session.call_tool(...)
```

### 3. Memory Leaks
- Limit pool size (MAX_POOL_SIZE = 10)
- Aggressive idle cleanup (5 minutes)
- Monitor process memory usage

### 4. Concurrent Access
- Use threading.Lock for pool access
- Each command gets its own session reference
- Pool manages lifecycle independently

## Testing Strategy

### Unit Tests
```python
def test_pool_reuses_process():
    """Test that second call reuses process."""
    pool = MCPRemotePool()

    # First call creates process
    session1 = await pool.get_session("test", "http://test")
    assert len(pool._pool) == 1

    # Second call reuses
    session2 = await pool.get_session("test", "http://test")
    assert len(pool._pool) == 1
    assert session1 == session2

def test_idle_cleanup():
    """Test that idle processes are cleaned up."""
    pool = MCPRemotePool()
    pool.IDLE_TIMEOUT = 1  # 1 second for testing

    session = await pool.get_session("test", "http://test")
    assert len(pool._pool) == 1

    time.sleep(2)
    pool._cleanup_idle_processes()

    assert len(pool._pool) == 0

def test_max_pool_size():
    """Test pool size limit."""
    pool = MCPRemotePool()
    pool.MAX_POOL_SIZE = 2

    await pool.get_session("app1", "http://test1")
    await pool.get_session("app2", "http://test2")
    await pool.get_session("app3", "http://test3")

    # Should have removed oldest
    assert len(pool._pool) == 2
    assert "app1" not in pool._pool
```

### Integration Tests
```python
def test_atlassian_performance():
    """Test real performance improvement."""
    import time

    # First command (cold start)
    start = time.time()
    run_command("tasak atlassian list")
    first_time = time.time() - start

    # Second command (should reuse)
    start = time.time()
    run_command("tasak atlassian create --project TEST")
    second_time = time.time() - start

    # Second should be much faster
    assert second_time < first_time / 2
```

## Rollout Plan

### Phase 1: Basic Pool (Week 1)
- Implement MCPRemotePool class
- Integrate with MCPRemoteClient
- Manual testing with Atlassian

### Phase 2: Robustness (Week 2)
- Add error recovery
- Add monitoring/logging
- Add configuration options

### Phase 3: Optimization (Week 3)
- Performance tuning
- Memory optimization
- Load testing

## Configuration Options

```yaml
# ~/.tasak/config.yaml
pool:
  enabled: true
  idle_timeout: 300  # seconds
  max_size: 10
  apps:
    atlassian:
      idle_timeout: 600  # Keep longer for frequently used
    github:
      idle_timeout: 180  # Shorter timeout
```

## Success Metrics

1. **Performance**: 70%+ reduction in command latency for repeated commands
2. **Reliability**: No zombie processes after 1000 operations
3. **Resource Usage**: Memory usage stable over time
4. **User Experience**: Instant response for subsequent commands

## Estimated Effort

- Basic implementation: 8 hours
- Testing and debugging: 4 hours
- Integration testing: 2 hours
- Documentation: 2 hours
- **Total: 2 days**

## Priority

**HIGH** - This is the biggest performance bottleneck in TASAK for remote MCP servers. Users running multiple commands experience significant delays.
