"""Core execution layer for TASAK.

Provides shared connection management and tool orchestration used by both
the daemon and direct CLI paths. This unifies list/call/cache/retry logic
behind a small, testable API.
"""

__all__ = [
    "connection_manager",
    "tool_service",
]
