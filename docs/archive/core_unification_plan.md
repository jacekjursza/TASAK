# TASAK Core Unification Plan

Goal: converge all MCP execution paths on a single, testable core so that both the daemon and direct CLI use the same business logic and transports. This eliminates duplicated code and flaky alternatives, and makes tests faster and deterministic.

## Objectives

- Single source of truth for MCP flows (list tools, call tool, caching, retries, timeouts).
- Pluggable transports (stdio, SSE, mcp-remote) behind clean interfaces.
- Two runtimes only:
  - DirectRuntime (in-process): used by CLI when daemon disabled (`TASAK_DEBUG=1` or `TASAK_NO_DAEMON=1`).
  - DaemonRuntime (out-of-process): FastAPI server calling the same core.
- Curated apps, classic MCP apps, and mcp-remote apps all call the same ToolService facade.
- Simpler tests: mock transports or inject fakes at the core boundary; minimal reliance on subprocesses.

## Target Design

Modules to introduce under `tasak/core/`:

- `tool_service.py`
  - Facade API: `ToolService.list_tools(app_name, app_config)`, `ToolService.call_tool(app_name, app_config, tool_name, args)`
  - Owns orchestration: cache policy, retries, error mapping, metrics hooks.

- `transports/base.py`
  - Protocols/ABCs for `TransportAdapter` with async `connect()`, `initialize()`, `list_tools()`, `call_tool()`, `close()`.
  - Error types and timeouts defined centrally in `errors.py`.

- `transports/stdio.py`, `transports/sse.py`, `transports/mcp_remote.py`
  - Concrete adapters encapsulating MCP SDK + mcp-remote process specifics.
  - No printing; logging only.

- `connection_manager.py`
  - Manages per-app connections (TTL, cleanup, metrics) with the same code in both runtimes.
  - In DaemonRuntime: long-lived, background cleanup.
  - In DirectRuntime: optional short-lived or in-memory cache (disabled by default for simplicity in tests).

- `factory.py`
  - Creates `TransportAdapter` from `app_config` (chooses stdio/sse/mcp-remote; applies flags like `sse-only`).
  - Returns `ConnectionHandle` to `ToolService`.

- `config.py`
  - Centralizes env flags (debug, log level, TTLs) and sensible defaults.

- `metrics.py` (optional, later)
  - Counters and timings; exported by daemon endpoints.

Runtime wrappers:

- Daemon (FastAPI): thin HTTP → `ToolService` calls; no business logic.
- Direct CLI: calls `ToolService` directly from `mcp_client.run_mcp_app` and curated backends.

## Status Update (current)

- Implemented
  - `tasak/core/connection_manager.py`: shared per‑app connection manager (stdio/SSE), TTL cleanup, snapshot metrics.
  - `tasak/core/tool_service.py`: orchestrates list/call, cache policy and a single retry on call failures.
  - Direct MCP path: `MCPRealClient` now delegates to `ToolService` (keeps on‑disk tool schema cache for compatibility).
  - Daemon runtime: endpoints `/tools/list` and `/tools/call` call `ToolService`; `/connections` and `/metrics` reflect the core manager snapshot. The daemon no longer carries bespoke pooling logic.
  - mcp-remote pool hardening: `MCPRemotePool` uses a dedicated asyncio loop and `ClientSession.__aenter__/__aexit__` for stable init/close; resolves hangs and cancellation scope errors during list/call and shutdown.

- Notable changes
  - Curated mcp-remote backends now route through ToolService using a thin adapter (transport `mcp-remote`), removing direct `MCPRemoteClient` usage in curated paths while keeping a compatibility shim in `mcp_remote_runner` for tests and CLI parity.
  - Transport adapters: added core `transports/mcp_remote.py` adapter (pool-backed) and interface stubs in `transports/base.py`. Stdio/SSE remain inlined in `ConnectionManager` for now.

Phases completed/partial
- Phase 1: DONE (core interfaces present; basic logic implemented).
- Phase 2: DONE (stdio/SSE supported from core; mcp-remote adapter added; config unification in core).
- Phase 3: DONE (direct MCP wired; curated mcp-remote now via core; legacy client retained only as a shim for runner/tests).
- Phase 4: DONE (daemon wired to core; thin wrapper; metrics improved).
- Phases 5–7: PENDING (further removals once external tests migrate, metrics expansion).

## Migration Plan (Phased)

Phase 0 — Freeze and Tests Guardrails
- Keep daemon working as-is. Add test env guard in E2E to bypass daemon by default: `TASAK_DEBUG=1` (already done for test MCP stdio).
- Add minimal conftest (future): set PATH to project `.venv/bin` and set `TASAK_NO_DAEMON=1` for local-only runs.

Phase 1 — Define Core Interfaces
- Add `tasak/core/transports/base.py`, `connection_manager.py`, `tool_service.py` skeletons with no-op adapters.
- Unit tests for the interfaces and basic error/timeout handling with a fake transport.

Phase 2 — Port Transports
- Implement `stdio.py` and `sse.py` using current MCP SDK calls.
- Implement `mcp_remote.py` (wraps `npx mcp-remote` via stdio; respects `--transport sse-only`, `--debug`).
- Move timeout/retry logic out of daemon into adapters/core.

Phase 3 — Wire DirectRuntime
- Change `mcp_client.run_mcp_app` to call `ToolService` (no client class instantiation). Keep CLI UX the same.
- Change `curated_app` to call `ToolService` for both `mcp` and `mcp-remote` (remove branching). Initially keep `TASAK_DEBUG=1` in E2E to avoid daemon in tests.

Phase 4 — Wire DaemonRuntime
- Replace daemon’s internal pool logic with `connection_manager` + `ToolService` calls.
- Daemon endpoints stay the same; internals simplified to “HTTP thin wrapper → ToolService”.

Phase 5 — Remove Duplicates
- Deprecate and remove bespoke clients (`MCPRealClient`, `MCPRemoteClient`, `mcp_remote_pool`, direct session code in daemon). Keep thin compatibility shims if needed during transition.

Phase 6 — Unify Curated Path
- Switch curated `mcp-remote` backend to the same `ToolService` (no special-casing). Update tests to patch transport/ToolService instead of concrete client classes.

Phase 7 — Polish & Metrics
- Add simple metrics collection in `metrics.py`, surface in daemon’s `/metrics`/`/connections`.
- Finalize logging levels and docs.

## Testing Strategy

- Unit tests (core):
  - Mock `TransportAdapter` (FakeTransport) to validate ToolService behavior (cache, retries, timeouts, error mapping).
  - Validate ConnectionManager TTL/cleanup deterministically.

- Integration tests (CLI, no daemon):
  - Use `TASAK_DEBUG=1`, ensure `PATH` includes `.venv/bin`.
  - Spawn the tiny stdio test server; verify normal flows and errors.

- Daemon tests:
  - Start daemon in-process or as a subprocess with `TASAK_DAEMON_LOG_LEVEL=ERROR`.
  - Call HTTP endpoints and assert JSON.
  - Verify `/connections` and `/metrics` match the core snapshot fields (age/idle/list_count/call_count).

- Test harness guardrails:
  - A shared fixture setting `TASAK_DEBUG=1` and PATH for E2E tests (avoids accidental daemon/network usage).
  - Small global per-call timeout to prevent hangs.

## Code Removals (after unification)

- `tasak/mcp_real_client.py`, `tasak/mcp_remote_client.py`, `tasak/mcp_remote_pool.py` — replaced by core + transports.
- Daemon’s custom pool — replaced by `connection_manager` from core.
- Special-case paths in `curated_app` — replaced with `ToolService` calls.

## Compatibility & Rollout

- Keep CLI flags and UX stable.
- Keep daemon endpoints stable.
- Introduce new internal APIs only under `tasak/core/…`.
- Migrate tests incrementally: first point them to ToolService/Transport patching; then remove legacy patches.

## Open Questions

- Where to store per-user auth cache for mcp-remote in a cross-platform way? (Currently mcp-remote manages its own.)
- Do we keep in-process connection cache for DirectRuntime on by default or only in daemon?
- How much per-call retry is acceptable by default (we currently use 1 retry on call in daemon)?

## Definition of Done

- Single core path used by CLI and Daemon.
- No duplicated logic for list/call/cache/retry/timeouts.
- E2E tests do not hang and do not depend on daemon by default.
- Documentation updated (architecture + README usage notes).
  - This file and daemon architecture doc reflect the current state and next steps.
