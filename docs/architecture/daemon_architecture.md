# TASAK Daemon — Architecture and Decisions

This document records the intentional design of the TASAK background daemon and how it supports TASAK’s role as a stateful session gateway for otherwise stateless CLI invocations.

## Goals

- Always-on, per-user, background service that amortizes connection startup costs across many CLI calls.
- Bridge stateless command executions to stateful sessions (connection pooling, caches, metrics later).
- Single-tenant model: 1 OS account = 1 TASAK user. No multi-user isolation in the daemon.
- Transparent to users: CLI benefits from pooling automatically; graceful fallback when daemon absent.
- Extensible transport support: stdio, SSE now; REST/SSH later.

## High-Level Architecture

```
User shell → tasak CLI → (auto-start/health-check) → TASAK Daemon (127.0.0.1:8765)
                                              ↘  direct (fallback when daemon unavailable)
```

- The daemon exposes a small local HTTP API (FastAPI, 127.0.0.1:8765) with endpoints for:
  - Health/Status: `GET /health`, `GET /connections`
  - Tools: `POST /tools/list/{app}`, `POST /tools/call/{app}`
  - Control: `POST /shutdown`
- Core integration: the daemon is now a thin HTTP wrapper over the shared core (`tasak/core`).
  - Connection management is provided by `ConnectionManager` (per‑app, TTL, cleanup).
  - Tool orchestration (list/call, cache, single retry) is provided by `ToolService`.
- The CLI uses a “smart client”: if daemon is healthy, it calls the daemon; if not, it falls back to direct MCP client.

## Operational Model

- Always-on by default: the CLI auto-starts the daemon when needed unless explicitly disabled or stopped by the user.
- Single user: designed for a single local OS account. No cross-user sharing or authentication between users.
- Local-only binding (127.0.0.1) to limit exposure. If future configurations open beyond localhost, introduce an auth token or switch to Unix domain sockets/Windows named pipes.

## Transport Strategies

- stdio (local MCP servers): pooled “warm” sessions avoid spawning a new process per command.
- SSE (remote MCP servers): pooled connections where feasible; cache tool schemas for faster list operations.
- mcp-remote (OAuth-backed remote via Node proxy):
  - Current: both `mcp-remote` apps and curated backends use `MCPRemoteClient`, which talks to a pooled `npx mcp-remote` stdio proxy.
  - Pooling is handled by `MCPRemotePool` (see “Runtime/Pooling details” below).
  - Future: route mcp-remote through the daemon/ToolService as well, once tests patch the HTTP boundary.

## Lifecycle & Management

- Start: CLI auto-starts the daemon on first use (unless disabled). Manual controls: `tasak daemon start|stop|restart|status|logs`.
- Stop: `tasak daemon stop` performs graceful shutdown via API, then ensures the uvicorn process fully terminates (no orphan processes) before removing the PID file.
- PID file: `~/.tasak/daemon.pid` (single-user). Logs: `~/.tasak/daemon.log`.
- Uptime: daemon reports true uptime (process start time) in `/health`.
- Cleanup: background task evicts expired/idle connections at a fixed interval.
 - Diagnostics endpoints: `GET /apps/{app}/ping?deep=true`, `GET /metrics`, `GET /connections`.

## Concurrency & Performance

- Core `ConnectionManager` keys connections per application name. Each connection carries its own TTL and lazy tool-list cache TTL.
- Critical sections are minimized inside the core; connection creation for one app does not block others.
- Debug mode (`TASAK_DEBUG=1`) bypasses the daemon to isolate issues and report timing information.

## Failure Modes & Fallback

- If the daemon is down or non-responsive, the CLI falls back to a direct MCP client and continues to work.
- For mcp-remote apps, the current flow uses `MCPRemoteClient` directly. Unification via daemon/ToolService is planned.
- Planned: per-app health checks (e.g., `GET /apps/{app}/ping` invoking a lightweight server call) to detect stale/broken sessions before use.
 - Expected logs like “terminated: other side closed” can appear when sessions are closed/retried; daemon adds timeouts and a single retry on tool calls to avoid hangs.

## Security Considerations

- Localhost-only listening, single user per OS account; no multi-tenant exposure by design.
- No auth on HTTP API in the default configuration; if exposure broadens, introduce an auth token or switch to local IPC.
- Logs are local to the user’s home directory.

## Configuration Knobs (current)

- Host/port (default `127.0.0.1:8765`).
- Debug bypass via `TASAK_DEBUG=1` (CLI talks directly to servers).
- Disable autostart: `TASAK_NO_DAEMON=1` or `~/.tasak/daemon.disabled` file (created by `tasak daemon stop`).
- Log level: `TASAK_DAEMON_LOG_LEVEL=INFO|DEBUG` or `tasak daemon start --log-level …`/`-v`.
- TTLs and timeouts (managed centrally in `tasak/core/config.py` and respected by CLI/daemon):
  - `TASAK_DAEMON_CONN_TTL` (default 300s)
  - `TASAK_DAEMON_CACHE_TTL` (default 900s)
  - `TASAK_MCP_INIT_TIMEOUT` (default 30s), `TASAK_MCP_INIT_ATTEMPTS` (default 2)
  - `TASAK_TOOL_LIST_TIMEOUT` (default 15s), `TASAK_TOOL_CALL_TIMEOUT` (default 30s)
  - `TASAK_TOOL_RETRIES` (default 1 retry on call)

## Runtime/Pooling details (current)

- Daemon runtime
  - Uses `tasak/core/connection_manager.py` and `tasak/core/tool_service.py` for all list/call operations.
  - Endpoints `/tools/list` and `/tools/call` invoke ToolService; `/connections`/`/metrics` reflect a snapshot from the core manager (age/idle, list/call counters).

- mcp-remote pooling (direct path)
  - `MCPRemotePool` holds a dedicated asyncio event loop thread that owns all stdio contexts and sessions.
  - New sessions call `await session.__aenter__()` before `initialize()`; shutdown uses `await session.__aexit__(...)` followed by closing the stdio context. This prevents anyio cancel-scope errors and avoids hangs during `tools/list`.
  - `shutdown()` marshals cleanup onto the dedicated loop and stops it cleanly.

## Near-Term Improvements (approved)

1) Daemon stop/uptime
   - Ensure `tasak daemon stop` actually terminates the uvicorn process after graceful shutdown; report real uptime.

2) mcp-remote path consistency
   - Unify curated-app path to also use the daemon (adjust tests to patch the daemon client layer or provide fakes for HTTP endpoints).

## Future Work

- Unify mcp-remote pooling inside the daemon (potentially via HTTP/WebSocket instead of stdio to proxy Node → Python cleanly).
- Add per-app health checks and metrics (init/list/call latencies, cache hit/miss counters).
- Optional daemon authentication or Unix socket transport.
- Auto-start-on-first-use with backoff and user-friendly diagnostics.
