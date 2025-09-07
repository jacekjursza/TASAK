# TASAK Architecture Overview

This document summarizes TASAK’s high-level architecture and points to deeper docs.

Components
- CLI (tasak): Entry point. Parses commands, loads/merges configs, dispatches to app runners.
- Core (shared): Connection management, tool listing/calling, schema caching. Used by both CLI and daemon.
- Transports: Adapters for MCP stdio/SSE and mcp-remote proxy.
- Daemon (FastAPI): Thin HTTP layer over the shared core for persistent connections and acceleration.

Key Flows
- CMD apps: Run local shell commands (curated or proxy modes).
- MCP apps: Connect to local MCP servers (stdio/SSE) and list/call tools.
- MCP-Remote apps: Use the mcp-remote proxy for cloud servers (OAuth, SSE); connections pooled.

Configuration
- Hierarchical merge: global `~/.tasak/<name>.yaml` + local `./<name>.yaml` or `./.tasak/<name>.yaml`.
- Default config name is `tasak.yaml`; wrappers can set `TASAK_CONFIG_NAME` to use another name.

Docs
- Daemon details: `docs/architecture/daemon_architecture.md`
- Usage guides: `docs/setup.md`, `docs/basic_usage.md`, `docs/advanced_usage.md`
