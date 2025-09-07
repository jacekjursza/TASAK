"""
Centralized configuration for TASAK core runtime.

Provides environment-backed defaults for TTLs, timeouts, retries and log level.
Both CLI direct runtime and the daemon should rely on these values.
"""

from __future__ import annotations

import os


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


# Connection + cache TTLs (seconds)
CONN_TTL: int = _env_int("TASAK_DAEMON_CONN_TTL", 300)
CACHE_TTL: int = _env_int("TASAK_DAEMON_CACHE_TTL", 900)

# Transport initialization behavior
INIT_TIMEOUT: float = _env_float("TASAK_MCP_INIT_TIMEOUT", 30.0)
INIT_ATTEMPTS: int = _env_int("TASAK_MCP_INIT_ATTEMPTS", 2)

# Per-call timeouts (seconds)
LIST_TIMEOUT: float = _env_float("TASAK_TOOL_LIST_TIMEOUT", 15.0)
CALL_TIMEOUT: float = _env_float("TASAK_TOOL_CALL_TIMEOUT", 30.0)

# Retries (applied to call only by default)
TOOL_RETRIES: int = _env_int("TASAK_TOOL_RETRIES", 1)

# Daemon log level (string level, normalized to upper)
LOG_LEVEL: str = os.environ.get("TASAK_DAEMON_LOG_LEVEL", "WARNING").upper()
